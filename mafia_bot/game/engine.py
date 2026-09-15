import asyncio
import logging
import random
from collections import Counter

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import db
from config import DAY_DISCUSSION_DURATION, NIGHT_DURATION, VOTE_DURATION
from economy import payout_game_results
from texts import ROLE_NAMES
from utils import (
    build_mafia_kill_keyboard,
    build_target_keyboard,
    build_vote_keyboard,
    build_vote_tally_text,
    mention,
)

from .manager import manager
from .models import Game, GameState, Role

logger = logging.getLogger(__name__)


def night_all_done(game: Game) -> bool:
    if len(game.mafia_votes) < game.night_mafia_needed:
        return False
    if game.night_doctor_needed and not game.doctor_acted:
        return False
    if game.night_detective_needed and not game.detective_acted:
        return False
    return True


async def _safe_send(bot: Bot, user_id: int, text: str, **kwargs) -> None:
    try:
        await bot.send_message(user_id, text, **kwargs)
    except (TelegramForbiddenError, TelegramBadRequest):
        pass


def check_win(game: Game) -> str | None:
    alive_mafia = sum(1 for p in game.players.values() if p.alive and p.role == Role.MAFIA)
    alive_others = sum(1 for p in game.players.values() if p.alive and p.role != Role.MAFIA)
    if alive_mafia == 0:
        return "town"
    if alive_mafia >= alive_others:
        return "mafia"
    return None


async def night_phase(bot: Bot, game: Game) -> None:
    game.state = GameState.NIGHT
    game.mafia_votes.clear()
    game.doctor_target = None
    game.doctor_acted = False
    game.detective_target = None
    game.detective_acted = False
    game.night_event = asyncio.Event()

    alive_mafia = [p for p in game.players.values() if p.alive and p.role == Role.MAFIA]
    alive_doctor = [p for p in game.players.values() if p.alive and p.role == Role.DOCTOR]
    alive_detective = [p for p in game.players.values() if p.alive and p.role == Role.DETECTIVE]

    game.night_mafia_needed = len(alive_mafia)
    game.night_doctor_needed = bool(alive_doctor)
    game.night_detective_needed = bool(alive_detective)

    await bot.send_message(
        game.chat_id,
        f"🌙 <b>{game.day_number}-tun boshlandi.</b>\n"
        "Shahar uyquga ketdi... Maxsus rollar harakat qilmoqda.",
    )

    mafia_ids = {p.user_id for p in alive_mafia}
    for m in alive_mafia:
        teammates = ", ".join(p.full_name for p in alive_mafia if p.user_id != m.user_id) or "yo'q"
        kb = build_mafia_kill_keyboard(game, m.user_id, exclude_ids=mafia_ids)
        await _safe_send(
            bot,
            m.user_id,
            f"🔪 Kimni yo'q qilmoqchisiz?\nSherik mafiyalar: {teammates}",
            reply_markup=kb,
        )

    for d in alive_doctor:
        kb = build_target_keyboard(game, exclude_ids=set(), prefix="d_save")
        await _safe_send(bot, d.user_id, "💊 Kimni himoya qilmoqchisiz?", reply_markup=kb)

    for c in alive_detective:
        kb = build_target_keyboard(game, exclude_ids={c.user_id}, prefix="c_check")
        await _safe_send(bot, c.user_id, "🕵️ Kimni tekshirmoqchisiz?", reply_markup=kb)

    if night_all_done(game):
        game.night_event.set()

    try:
        await asyncio.wait_for(game.night_event.wait(), timeout=NIGHT_DURATION)
    except asyncio.TimeoutError:
        pass

    mafia_target = None
    if game.mafia_votes:
        counts = Counter(game.mafia_votes.values())
        top = counts.most_common()
        max_count = top[0][1]
        candidates = [uid for uid, c in top if c == max_count]
        mafia_target = random.choice(candidates)

    victim_id = mafia_target if mafia_target != game.doctor_target else None
    rifle_used = bool(game.mafia_rifle_users)

    if victim_id is not None:
        victim = game.players[victim_id]

        if victim.items.get("mirror", 0) > 0 and await db.consume_item(victim.user_id, "mirror"):
            victim.items["mirror"] -= 1
            alive_mafia_ids = [p.user_id for p in game.players.values() if p.alive and p.role == Role.MAFIA]
            if alive_mafia_ids:
                bounced = game.players[random.choice(alive_mafia_ids)]
                bounced.alive = False
                await _safe_send(bot, victim.user_id, "🔮 Sehrli oynangiz o'qni qaytardi! Siz omon qoldingiz.")
                await bot.send_message(
                    game.chat_id,
                    f"🔮 Tun natijasi: mafiyaning o'qi qaytib, <b>{mention(bounced)}</b> halok bo'ldi.\n"
                    f"U — {ROLE_NAMES[bounced.role]} edi.",
                )
                return
            victim_id = None

    if rifle_used:
        for uid in list(game.mafia_rifle_users):
            if await db.consume_item(uid, "rifle"):
                shooter = game.players.get(uid)
                if shooter:
                    shooter.items["rifle"] = max(0, shooter.items.get("rifle", 0) - 1)

    if victim_id is not None:
        victim = game.players[victim_id]

        if not rifle_used and victim.items.get("shield", 0) > 0 and await db.consume_item(victim.user_id, "shield"):
            victim.items["shield"] -= 1
            await _safe_send(bot, victim.user_id, "🛡 Himoyangiz sizni mafiya hujumidan saqlab qoldi!")
            await bot.send_message(game.chat_id, "🌤 Tun tinch o'tdi. Bu safar hech kim halok bo'lmadi.")
            return

        victim.alive = False
        await bot.send_message(
            game.chat_id,
            f"☠️ Tun natijasi: <b>{mention(victim)}</b> halok bo'ldi.\n"
            f"U — {ROLE_NAMES[victim.role]} edi.",
        )
    else:
        await bot.send_message(
            game.chat_id,
            "🌤 Tun tinch o'tdi. Bu safar hech kim halok bo'lmadi.",
        )


async def day_phase(bot: Bot, game: Game) -> None:
    game.state = GameState.DAY_DISCUSSION
    alive = [p for p in game.players.values() if p.alive]
    names = "\n".join(f"• {mention(p)}" for p in alive)
    await bot.send_message(
        game.chat_id,
        f"☀️ <b>{game.day_number}-kun.</b>\nTirik qolganlar:\n{names}\n\n"
        f"Muhokama vaqti: {DAY_DISCUSSION_DURATION} soniya.",
    )
    await asyncio.sleep(DAY_DISCUSSION_DURATION)

    game.state = GameState.DAY_VOTING
    game.day_votes.clear()
    game.vote_needed = len(alive)
    game.vote_event = asyncio.Event()

    kb = build_vote_keyboard(game)
    msg = await bot.send_message(game.chat_id, build_vote_tally_text(game), reply_markup=kb)
    game.vote_message_id = msg.message_id

    try:
        await asyncio.wait_for(game.vote_event.wait(), timeout=VOTE_DURATION)
    except asyncio.TimeoutError:
        pass

    if game.day_votes:
        counts = Counter(v for v in game.day_votes.values() if v is not None)
        if counts:
            top = counts.most_common()
            max_count = top[0][1]
            candidates = [uid for uid, c in top if c == max_count]
            if len(candidates) == 1:
                eliminated = game.players[candidates[0]]

                if eliminated.items.get("vote_shield", 0) > 0 and await db.consume_item(
                    eliminated.user_id, "vote_shield"
                ):
                    eliminated.items["vote_shield"] -= 1
                    await bot.send_message(
                        game.chat_id,
                        f"⚖️ {mention(eliminated)} eng ko'p ovoz oldi, lekin "
                        "Ovozdan himoya buyumi tufayli omon qoldi!",
                    )
                    return

                eliminated.alive = False
                await bot.send_message(
                    game.chat_id,
                    f"⚖️ Shahar ovoz berdi: <b>{mention(eliminated)}</b> haydab "
                    f"chiqarildi.\nU — {ROLE_NAMES[eliminated.role]} edi.",
                )
                return

    await bot.send_message(game.chat_id, "⚖️ Ovozlar teng bo'ldi yoki hech kim ovoz bermadi — bugun hech kim haydalmadi.")


async def finish_game(bot: Bot, game: Game, winner: str) -> None:
    game.state = GameState.FINISHED
    lines = ["🏁 <b>O'YIN TUGADI</b>", ""]
    if winner == "town":
        lines.append("🎉 <b>Tinch aholi g'alaba qozondi!</b> Barcha mafiyalar tutildi.")
    else:
        lines.append("🔪 <b>Mafiya g'alaba qozondi!</b> Shahar ularning qo'liga o'tdi.")

    lines.append("")
    lines.append("<b>👥 Barcha ishtirokchilar va rollari:</b>")
    for p in game.players.values():
        status = "🟢 tirik" if p.alive else "⚰️ halok"
        lines.append(f"• {p.full_name} — {ROLE_NAMES[p.role]} ({status})")

    payout_lines = await payout_game_results(game, winner)
    lines.append("")
    lines.append("<b>💰 Mukofotlar:</b>")
    lines.extend(payout_lines)

    await bot.send_message(game.chat_id, "\n".join(lines))
    manager.remove_game(game.chat_id)


async def run_game(bot: Bot, game: Game) -> None:
    game.task = asyncio.current_task()
    try:
        while True:
            game.day_number += 1
            await night_phase(bot, game)
            winner = check_win(game)
            if winner:
                await finish_game(bot, game, winner)
                return

            await day_phase(bot, game)
            winner = check_win(game)
            if winner:
                await finish_game(bot, game, winner)
                return
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Game loop error in chat %s", game.chat_id)
        try:
            await bot.send_message(game.chat_id, "⚠️ O'yinda kutilmagan xatolik yuz berdi, o'yin to'xtatildi.")
        except Exception:
            pass
        manager.remove_game(game.chat_id)
