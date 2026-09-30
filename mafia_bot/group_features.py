"""🏰 Guruh premiumi imkoniyatlari (faqat premium faol bo'lganda): haftalik statistika, guruh unvoni, turnir."""
import asyncio
import logging
import random
import time
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import cosmetics
import db
from config import TIMEZONE_OFFSET_HOURS
from economy import (
    GROUP_STATS_ACTIVE,
    GROUP_STATS_HOUR,
    GROUP_STATS_TOP,
    GROUP_STATS_WEEKDAY,
    GROUP_TITLE_GAMES,
    TOURNAMENT_MIN_PLAYERS,
    TOURNAMENT_MVP_TOP,
    TOURNAMENT_POINTS_ALIVE,
    TOURNAMENT_POINTS_MVP,
    TOURNAMENT_POINTS_WIN,
    TOURNAMENT_PRIZE_SPLIT,
    TOURNAMENT_TABLE_SIZE,
    TOURNAMENT_TIMEOUT_HOURS,
    did_win,
)
from i18n import get_texts, group_lang, texts_for_user
from utils import esc

logger = logging.getLogger(__name__)
TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))
LOOP_INTERVAL = 600
WEEK = timedelta(days=7)


async def _send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


# ---------- O'yin yakunida ----------


async def on_game_finished(bot: Bot, game, winner: str) -> list[str]:
    """Premium guruhda: guruh unvonlarini beradi va turnir o'yinini hisoblaydi.
    Guruhdagi yakuniy xabarga qo'shiladigan qatorlarni (turnir jadvali) qaytaradi."""
    if not await db.is_group_premium(game.chat_id):
        return []
    await _grant_group_titles(bot, game)
    return await _count_tournament_game(bot, game, winner)


async def _grant_group_titles(bot: Bot, game) -> None:
    key = cosmetics.group_title_key(game.chat_id)
    title = await cosmetics.group_title_text(game.chat_id)
    chat = await db.get_group_title(game.chat_id) or str(game.chat_id)
    for p in game.players.values():
        if p.afk or await db.games_in_chat(p.user_id, game.chat_id) < GROUP_TITLE_GAMES:
            continue
        if await db.grant_cosmetic(p.user_id, key):
            L = get_texts(p.lang)
            await _send(bot, p.user_id, L.GROUP_TITLE_GRANTED.format(chat=esc(chat), games=GROUP_TITLE_GAMES, title=title))


def tournament_points(game, winner: str) -> dict[int, tuple[int, int]]:
    """{user_id: (ochko, g'alaba)}: g'alaba 3, oxirigacha tirik +1, o'yindagi eng yaxshi 3 MVP +2; AFK — 0."""
    ranked = sorted(
        (p for p in game.players.values() if not p.afk and game.mvp.get(p.user_id, 0) > 0),
        key=lambda p: game.mvp[p.user_id],
        reverse=True,
    )
    mvp_ids = {p.user_id for p in ranked[:TOURNAMENT_MVP_TOP]}
    scores = {}
    for p in game.players.values():
        if p.afk:
            continue
        won = did_win(p, winner)
        points = (TOURNAMENT_POINTS_WIN if won else 0) + (TOURNAMENT_POINTS_ALIVE if p.alive else 0)
        points += TOURNAMENT_POINTS_MVP if p.user_id in mvp_ids else 0
        scores[p.user_id] = (points, int(won))
    return scores


def rank_scores(rows) -> list:
    """Ochko, keyin g'alabalar soni bo'yicha; teng bo'lsa — tasodifiy."""
    rows = list(rows)
    random.shuffle(rows)
    return sorted(rows, key=lambda r: (r["points"], r["wins"]), reverse=True)


def table_text(rows, played: int, total: int, L) -> str:
    lines = [L.TOURNAMENT_TABLE_HEADER.format(played=played, games=total)]
    ranked = sorted(rows, key=lambda r: (r["points"], r["wins"]), reverse=True)[:TOURNAMENT_TABLE_SIZE]
    if not ranked:
        lines.append(L.TOURNAMENT_TABLE_EMPTY)
    for i, row in enumerate(ranked, 1):
        lines.append(L.TOURNAMENT_TABLE_LINE.format(
            place=i, name=esc(row["full_name"]), points=row["points"], wins=row["wins"]
        ))
    return "\n".join(lines)


async def _count_tournament_game(bot: Bot, game, winner: str) -> list[str]:
    t = await db.active_tournament(game.chat_id)
    # Faqat turnir e'lon qilingandan keyin boshlangan, kamida TOURNAMENT_MIN_PLAYERS kishilik o'yinlar.
    if not t or len(game.players) < TOURNAMENT_MIN_PLAYERS or (game.started_at or 0) < t["created_at"]:
        return []
    played = await db.add_tournament_game(t["tournament_id"], tournament_points(game, winner))
    L = get_texts(game.settings.lang)
    lines = ["", table_text(await db.tournament_scores(t["tournament_id"]), played, t["games_total"], L)]
    if played >= t["games_total"]:
        lines += ["", await finish_tournament(bot, t, L)]
    return lines


async def finish_tournament(bot: Bot, t, L) -> str:
    """Sovrinni 50/30/20 taqsimlaydi (pastga yaxlitlanadi), qoldiq adminga qaytadi. Guruh uchun matn."""
    if not await db.set_tournament_status(t["tournament_id"], "active", "finished"):
        return ""
    ranked = rank_scores(await db.tournament_scores(t["tournament_id"]))
    prize, paid, lines = t["prize"], 0, []
    for place, (row, percent) in enumerate(zip(ranked, TOURNAMENT_PRIZE_SPLIT), 1):
        amount = prize * percent // 100
        if amount <= 0:
            continue
        await db.add_balance(row["user_id"], diamonds=amount)
        paid += amount
        lines.append(L.TOURNAMENT_WINNER_LINE.format(place=place, name=esc(row["full_name"]), prize=amount))
        user_texts = await texts_for_user(row["user_id"])
        await _send(bot, row["user_id"], user_texts.TOURNAMENT_PRIZE_PRIVATE.format(place=place, prize=amount))
    if prize - paid > 0:
        await db.add_balance(t["admin_id"], diamonds=prize - paid)
    return L.TOURNAMENT_FINISHED.format(winners="\n".join(lines) if lines else L.TOURNAMENT_NO_WINNERS)


def tournament_game_running(t) -> bool:
    """Turnir e'lon qilingandan keyin boshlangan o'yin hozir ketyaptimi (u turnir o'yini hisoblanadi)."""
    from game.manager import manager

    game = manager.get_game(t["chat_id"])
    return bool(game and game.started_at and game.started_at >= t["created_at"])


async def cancel_tournament(t) -> bool:
    """Faqat birinchi o'yin boshlanguncha; sovrin adminga qaytadi."""
    if t["games_played"] > 0 or tournament_game_running(t) or not await db.set_tournament_status(t["tournament_id"], "active", "cancelled"):
        return False
    await db.add_balance(t["admin_id"], diamonds=t["prize"])
    return True


# ---------- Fon vazifalari ----------


def week_start(now: datetime) -> datetime:
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


async def send_weekly_stats(bot: Bot, now: datetime | None = None) -> int:
    """Dushanba GROUP_STATS_HOUR dan keyin premium guruhlarga o'tgan hafta statistikasi (bir marta)."""
    now = now or datetime.now(TZ)
    if now.weekday() != GROUP_STATS_WEEKDAY or now.hour < GROUP_STATS_HOUR:
        return 0
    this_week = week_start(now)
    since, until = this_week - WEEK, this_week
    sent = 0
    for chat_id in await db.premium_group_ids():
        if not await db.mark_group_weekly_stats(chat_id, int(this_week.timestamp())):
            continue
        stats = await db.group_week_stats(chat_id, int(since.timestamp()), int(until.timestamp()))
        games = sum(stats["by_winner"].values())
        if games == 0:
            continue  # o'yin bo'lmagan hafta — xabar yuborilmaydi
        L = get_texts(await group_lang(chat_id))
        players = stats["players"]
        top = sorted(players, key=lambda r: r["points"], reverse=True)[:GROUP_STATS_TOP]
        active = sorted(players, key=lambda r: r["games"], reverse=True)[:GROUP_STATS_ACTIVE]
        text = L.GROUP_STATS_TEXT.format(
            since=since.strftime("%d.%m"),
            until=(until - timedelta(days=1)).strftime("%d.%m"),
            games=games,
            town=round(100 * stats["by_winner"].get("town", 0) / games),
            mafia=round(100 * stats["by_winner"].get("mafia", 0) / games),
            top_n=GROUP_STATS_TOP,
            top="\n".join(L.GROUP_STATS_TOP_LINE.format(place=i, name=esc(r["full_name"]), points=r["points"])
                          for i, r in enumerate(top, 1)),
            active="\n".join(L.GROUP_STATS_ACTIVE_LINE.format(place=i, name=esc(r["full_name"]), games=r["games"])
                             for i, r in enumerate(active, 1)),
        )
        await _send(bot, chat_id, text)
        sent += 1
    return sent


async def finish_expired_tournaments(bot: Bot, now: float | None = None) -> int:
    """TOURNAMENT_TIMEOUT_HOURS ichida tugamagan turnirlar joriy natijalar bo'yicha yakunlanadi."""
    now = now or time.time()
    finished = 0
    for t in await db.expired_tournaments(int(now - TOURNAMENT_TIMEOUT_HOURS * 3600)):
        L = get_texts(await group_lang(t["chat_id"]))
        text = await finish_tournament(bot, t, L)
        if text:
            await _send(bot, t["chat_id"], text)
            finished += 1
    return finished


async def group_features_loop(bot: Bot) -> None:
    while True:
        try:
            await send_weekly_stats(bot)
            await finish_expired_tournaments(bot)
        except Exception:
            logger.exception("Guruh premiumi fon vazifasida xatolik")
        await asyncio.sleep(LOOP_INTERVAL)
