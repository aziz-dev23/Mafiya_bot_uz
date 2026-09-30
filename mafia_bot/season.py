"""🎟 Mavsum chiptasi: har oy bitta mavsum (Toshkent vaqti), XP o'yinlardan, mukofotlar avtomatik."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import db
from config import TIMEZONE_OFFSET_HOURS
from economy import (
    COSMETICS_BY_KEY,
    CURRENCY_COLUMN,
    ITEMS,
    SEASON_COSMETICS,
    SEASON_FIRST_MONTH,
    SEASON_MAX_LEVEL,
    SEASON_PREMIUM_PRICE_DIAMONDS,
    SEASON_REMINDER_DAYS_BEFORE_END,
    SEASON_XP_FIRST_GAME_BONUS,
    SEASON_XP_LOSE,
    SEASON_XP_MIN_PLAYERS,
    SEASON_XP_WIN,
    season_free_rewards,
    season_level_for_xp,
    season_premium_rewards,
    season_xp_for_level,
)
from i18n import get_texts, texts_for_user

logger = logging.getLogger(__name__)

TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))
REMINDER_CHECK_INTERVAL = 3600


def _month_index(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def current_season(now: datetime | None = None) -> int | None:
    """Joriy mavsum raqami (1 dan boshlab); 1-mavsum boshlanmagan bo'lsa None."""
    now = now or datetime.now(TZ)
    n = _month_index(now.year, now.month) - _month_index(*SEASON_FIRST_MONTH) + 1
    return n if n >= 1 else None


def season_start(season: int) -> datetime:
    index = _month_index(*SEASON_FIRST_MONTH) + season - 1
    return datetime(index // 12, index % 12 + 1, 1, tzinfo=TZ)


def season_end(season: int) -> datetime:
    """Keyingi mavsum boshlanish vaqti (shu mavsum oxirgi kun 23:59:59 dan keyin)."""
    return season_start(season + 1)


def days_left(season: int, now: datetime | None = None) -> int:
    now = now or datetime.now(TZ)
    return max(0, (season_end(season).date() - now.date()).days)


def season_name(season: int, L) -> str:
    return L.SEASON_NAMES.get(season) or L.SEASON_DEFAULT_NAME.format(n=season)


def reward_text(reward: tuple, season: int, L) -> str:
    kind = reward[0]
    if kind == "dollar":
        return L.REWARD_DOLLAR.format(amount=reward[1])
    if kind == "coin":
        return L.REWARD_COIN.format(amount=reward[1])
    if kind == "diamond":
        return L.REWARD_DIAMOND.format(amount=reward[1])
    if kind == "item":
        key, count = reward[1], reward[2]
        return L.REWARD_ITEM.format(count=count, emoji=ITEMS[key]["emoji"], name=L.ITEM_NAMES[key])
    key = SEASON_COSMETICS.get(season, {}).get(reward[1])
    return L.COSMETIC_NAMES.get(key, "?") if key else "?"


async def _apply_reward(user_id: int, season: int, reward: tuple) -> None:
    kind = reward[0]
    if kind in CURRENCY_COLUMN:
        await db.add_balance(user_id, **{CURRENCY_COLUMN[kind]: reward[1]})
    elif kind == "item":
        await db.add_item(user_id, reward[1], reward[2])
    elif kind == "cosmetic":
        key = SEASON_COSMETICS.get(season, {}).get(reward[1])
        if key in COSMETICS_BY_KEY:
            await db.grant_cosmetic(user_id, key)


async def grant_pending_rewards(user_id: int, season: int) -> list[tuple]:
    """Yetilgan, lekin hali berilmagan darajalar mukofotini beradi (bepul va premium yo'lak).
    Berilgan mukofotlar ro'yxatini qaytaradi."""
    row = await db.season_progress(user_id, season)
    if row is None:
        return []
    level = season_level_for_xp(row["xp"])
    granted: list[tuple] = []
    for lvl in range(row["rewarded_free"] + 1, level + 1):
        for reward in season_free_rewards(lvl):
            await _apply_reward(user_id, season, reward)
            granted.append(reward)
    premium_done = row["rewarded_premium"]
    if row["premium"]:
        for lvl in range(row["rewarded_premium"] + 1, level + 1):
            for reward in season_premium_rewards(lvl):
                await _apply_reward(user_id, season, reward)
                granted.append(reward)
        premium_done = level
    await db.set_season_rewarded(user_id, season, max(level, row["rewarded_free"]), max(premium_done, 0))
    return granted


async def award_game_xp(user_id: int, won: bool, player_count: int, now: datetime | None = None):
    """O'yin uchun XP beradi. (xp, daraja, yangi mukofotlar) yoki XP berilmasa None qaytaradi.
    AFK sababli chiqarilganlar uchun chaqirilmaydi."""
    now = now or datetime.now(TZ)
    season = current_season(now)
    if season is None or player_count < SEASON_XP_MIN_PLAYERS:
        return None
    day = now.strftime("%Y-%m-%d")
    row = await db.season_progress(user_id, season)
    xp = SEASON_XP_WIN if won else SEASON_XP_LOSE
    if row is None or row["last_xp_day"] != day:
        xp += SEASON_XP_FIRST_GAME_BONUS
    await db.add_season_xp(user_id, season, xp, day)
    rewards = await grant_pending_rewards(user_id, season)
    row = await db.season_progress(user_id, season)
    return xp, season_level_for_xp(row["xp"]), rewards


async def buy_premium(user_id: int, now: datetime | None = None) -> tuple[str, list[tuple]]:
    """Premium yo'lakni olmosga sotib oladi. Holat: "no_season", "already", "no_funds" yoki "ok"."""
    season = current_season(now)
    if season is None:
        return "no_season", []
    row = await db.season_progress(user_id, season)
    if row is not None and row["premium"]:
        return "already", []
    if not await db.spend_balance(user_id, "diamonds", SEASON_PREMIUM_PRICE_DIAMONDS):
        return "no_funds", []
    if not await db.set_season_premium(user_id, season):
        # Ikki marta tez bosilgan: premium allaqachon yoqilgan — to'lov qaytariladi.
        await db.add_balance(user_id, diamonds=SEASON_PREMIUM_PRICE_DIAMONDS)
        return "already", []
    return "ok", await grant_pending_rewards(user_id, season)


def next_reward_line(level: int, rewards_fn, season: int, L) -> str:
    if level >= SEASON_MAX_LEVEL:
        return L.SEASON_NO_MORE_REWARDS
    nxt = level + 1
    rewards = ", ".join(reward_text(r, season, L) for r in rewards_fn(nxt))
    return L.SEASON_REWARD_AT.format(level=nxt, rewards=rewards)


async def season_view(user_id: int, L, now: datetime | None = None) -> tuple[str, bool]:
    """/mavsum matni va premium tugmasi kerakligi."""
    now = now or datetime.now(TZ)
    season = current_season(now)
    if season is None:
        first = season_start(1)
        return L.SEASON_NOT_STARTED.format(name=season_name(1, L), date=first.strftime("%d.%m.%Y")), False
    row = await db.season_progress(user_id, season)
    xp = row["xp"] if row else 0
    premium = bool(row and row["premium"])
    level = season_level_for_xp(xp)
    if level >= SEASON_MAX_LEVEL:
        next_line = L.SEASON_MAX_REACHED
    else:
        next_line = L.SEASON_NEXT_LEVEL.format(xp=season_xp_for_level(level + 1) - xp)
    text = L.SEASON_TEXT.format(
        name=season_name(season, L), n=season, days=days_left(season, now),
        level=level, max_level=SEASON_MAX_LEVEL, xp=xp, next_line=next_line,
        next_free=next_reward_line(level, season_free_rewards, season, L),
        premium_state=L.SEASON_PREMIUM_ON if premium else L.SEASON_PREMIUM_OFF,
        next_premium=next_reward_line(level, season_premium_rewards, season, L),
        xp_win=SEASON_XP_WIN, xp_lose=SEASON_XP_LOSE, xp_bonus=SEASON_XP_FIRST_GAME_BONUS,
        min_players=SEASON_XP_MIN_PLAYERS,
    )
    return text, not premium


async def send_reminders(bot: Bot, now: datetime | None = None) -> int:
    """Mavsum tugashiga SEASON_REMINDER_DAYS_BEFORE_END kun qolganda qatnashchilarga bir marta eslatma."""
    now = now or datetime.now(TZ)
    season = current_season(now)
    if season is None or days_left(season, now) > SEASON_REMINDER_DAYS_BEFORE_END:
        return 0
    sent = 0
    for user_id in await db.season_players_to_remind(season):
        L = await texts_for_user(user_id)
        row = await db.season_progress(user_id, season)
        text = L.SEASON_REMINDER.format(
            name=season_name(season, L), days=days_left(season, now), level=season_level_for_xp(row["xp"])
        )
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    return sent


async def season_reminder_loop(bot: Bot) -> None:
    while True:
        try:
            await send_reminders(bot)
        except Exception:
            logger.exception("Mavsum eslatmalarida xatolik")
        await asyncio.sleep(REMINDER_CHECK_INTERVAL)


def rewards_summary(rewards: list[tuple], season: int, lang: str | None) -> str:
    L = get_texts(lang)
    return ", ".join(reward_text(r, season, L) for r in rewards)
