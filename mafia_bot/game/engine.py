import asyncio
import logging
import random
from collections import Counter
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

import db
from config import DAWN_DURATION, DAY_DISCUSSION_DURATION, NIGHT_DURATION, VOTE_DURATION
from economy import HITMAN_CONTRACT_BONUS_DOLLARS, MINER_SLIP_CHANCE, payout_game_results
from texts import ROLE_NAMES
from utils import (
    build_don_check_keyboard,
    build_mafia_kill_keyboard,
    build_target_keyboard,
    build_vote_keyboard,
    build_vote_tally_text,
    mention,
)

from .manager import manager
from .models import Game, GameState, Role

logger = logging.getLogger(__name__)

MAFIA_TEAM_ROLES = (Role.MAFIA, Role.DON)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
DAY_IMAGE_PATH = ASSETS_DIR / "day.jpg"
NIGHT_IMAGE_PATH = ASSETS_DIR / "night.jpg"
_PHASE_IMAGE_CACHE: dict[str, str] = {}
_BOT_USERNAME_CACHE: str | None = None


async def _send_phase_image(bot: Bot, chat_id: int, path: Path, cache_key: str, caption: str) -> None:
    """Sends the day/night banner as a photo; caches the Telegram file_id after the first upload."""
    try:
        photo = _PHASE_IMAGE_CACHE.get(cache_key) or FSInputFile(path)
        msg = await bot.send_photo(chat_id, photo=photo, caption=caption)
        if cache_key not in _PHASE_IMAGE_CACHE and msg.photo:
            _PHASE_IMAGE_CACHE[cache_key] = msg.photo[-1].file_id
    except (TelegramBadRequest, TelegramForbiddenError, FileNotFoundError):
        await bot.send_message(chat_id, caption)


async def _get_bot_username(bot: Bot) -> str:
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE is None:
        me = await bot.get_me()
        _BOT_USERNAME_CACHE = me.username
    return _BOT_USERNAME_CACHE


def _goto_bot_keyboard(username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🤖 Botga o'tish", url=f"https://t.me/{username}")]]
    )


def _alive_list_text(game: Game) -> str:
    alive = [p for p in game.players.values() if p.alive]
    return "\n".join(f"{i}. {p.full_name}" for i, p in enumerate(alive, 1))


def night_all_done(game: Game) -> bool:
    if len(game.mafia_votes) < game.night_mafia_needed:
        return False
    if game.night_doctor_needed and not game.doctor_acted:
        return False
    if game.night_detective_needed and not game.detective_acted:
        return False
    if game.night_killer_needed and not game.killer_acted:
        return False
    if game.night_hitman_needed and not game.hitman_acted:
        return False
    if game.night_poisoner_needed and not game.poisoner_acted:
        return False
    if game.night_wanderer_needed and not game.wanderer_acted:
        return False
    return True


async def _safe_send(bot: Bot, user_id: int, text: str, **kwargs) -> None:
    try:
        await bot.send_message(user_id, text, **kwargs)
    except (TelegramForbiddenError, TelegramBadRequest):
        pass


def check_win(game: Game) -> str | None:
    alive_players = [p for p in game.players.values() if p.alive]
    if len(alive_players) == 1 and alive_players[0].role == Role.KILLER:
        return "killer"

    alive_mafia = sum(1 for p in alive_players if p.role in MAFIA_TEAM_ROLES)
    alive_others = sum(1 for p in alive_players if p.role not in MAFIA_TEAM_ROLES)
    if alive_mafia == 0:
        return "town"
    if alive_mafia >= alive_others:
        return "mafia"
    return None


async def night_phase(bot: Bot, game: Game) -> None:
    game.state = GameState.NIGHT
    game.mafia_votes.clear()
    game.mafia_rifle_users.clear()
    game.doctor_target = None
    game.doctor_acted = False
    game.detective_target = None
    game.detective_acted = False
    game.killer_target = None
    game.killer_acted = False
    game.hitman_target = None
    game.hitman_acted = False
    game.poisoner_acted = False
    game.wanderer_target = None
    game.wanderer_acted = False
    game.night_event = asyncio.Event()

    tonight_deaths: set[int] = set()

    # O'tgan tundagi Kezuvchi dorisi shu kecha ta'sir qiladi (agar bor bo'lsa).
    for victim_id, die_night in list(game.pending_poison.items()):
        if die_night != game.day_number:
            continue
        del game.pending_poison[victim_id]
        victim = game.players.get(victim_id)
        if victim and victim.alive:
            victim.alive = False
            tonight_deaths.add(victim.user_id)
            await bot.send_message(
                game.chat_id,
                f"💊 Tun natijasi: <b>{mention(victim)}</b> kezuvchining dorisidan halok bo'ldi.\n"
                f"U — {ROLE_NAMES[victim.role]} edi.",
            )

    alive_mafia = [p for p in game.players.values() if p.alive and p.role in MAFIA_TEAM_ROLES]
    alive_doctor = [p for p in game.players.values() if p.alive and p.role == Role.DOCTOR]
    alive_detective = [p for p in game.players.values() if p.alive and p.role == Role.DETECTIVE]
    alive_killer = [p for p in game.players.values() if p.alive and p.role == Role.KILLER]
    alive_hitman = [p for p in game.players.values() if p.alive and p.role == Role.HITMAN]
    alive_poisoner = [p for p in game.players.values() if p.alive and p.role == Role.POISONER]
    alive_wanderer = [p for p in game.players.values() if p.alive and p.role == Role.WANDERER]
    alive_don = [p for p in game.players.values() if p.alive and p.role == Role.DON]

    game.night_mafia_needed = len(alive_mafia)
    game.night_doctor_needed = bool(alive_doctor)
    game.night_detective_needed = bool(alive_detective)
    game.night_killer_needed = bool(alive_killer)
    game.night_hitman_needed = bool(alive_hitman)
    game.night_poisoner_needed = bool(alive_poisoner)
    game.night_wanderer_needed = bool(alive_wanderer)

    await _send_phase_image(
        bot,
        game.chat_id,
        NIGHT_IMAGE_PATH,
        "night",
        f"🌌 <b>Tun — {game.day_number}</b>\n"
        "Ko'chaga faqat jasur va qo'rqmas odamlar chiqishdi. Ertalab tirik "
        "qolganlarni sanaymiz...",
    )

    username = await _get_bot_username(bot)
    await bot.send_message(
        game.chat_id,
        f"👥 <b>Tirik o'yinchilar:</b>\n{_alive_list_text(game)}\n\n"
        f"⏳ Tonggacha {NIGHT_DURATION} soniya qoldi.",
        reply_markup=_goto_bot_keyboard(username),
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

    for k in alive_killer:
        kb = build_target_keyboard(game, exclude_ids={k.user_id}, prefix="q_kill")
        await _safe_send(bot, k.user_id, "🔪 Kimni yo'q qilmoqchisiz? (mustaqil)", reply_markup=kb)

    for h in alive_hitman:
        kb = build_target_keyboard(game, exclude_ids={h.user_id}, prefix="yq_kill")
        await _safe_send(bot, h.user_id, "🥷 Kimni yo'q qilmoqchisiz? (mustaqil)", reply_markup=kb)

    for p_ in alive_poisoner:
        kb = build_target_keyboard(game, exclude_ids={p_.user_id}, prefix="kez_dose")
        await _safe_send(bot, p_.user_id, "💊 Kimga dori bermoqchisiz?", reply_markup=kb)

    for w in alive_wanderer:
        kb = build_target_keyboard(game, exclude_ids={w.user_id}, prefix="daydi_visit")
        await _safe_send(bot, w.user_id, "🚶 Kimning oldiga bormoqchisiz?", reply_markup=kb)

    for don in alive_don:
        if game.don_check_used:
            continue
        kb = build_don_check_keyboard(game, exclude_ids=mafia_ids)
        await _safe_send(
            bot,
            don.user_id,
            "🎩 Xohlasangiz, kimningdir Komissar ekanini aniqlashga urinib ko'rishingiz mumkin "
            "(butun o'yin davomida faqat bir marta):",
            reply_markup=kb,
        )

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
    mafia_resolved = False

    if victim_id is not None:
        victim = game.players[victim_id]

        if victim.items.get("mirror", 0) > 0 and await db.consume_item(victim.user_id, "mirror"):
            victim.items["mirror"] -= 1
            alive_mafia_ids = [p.user_id for p in game.players.values() if p.alive and p.role in MAFIA_TEAM_ROLES]
            if alive_mafia_ids:
                bounced = game.players[random.choice(alive_mafia_ids)]
                bounced.alive = False
                tonight_deaths.add(bounced.user_id)
                await _safe_send(bot, victim.user_id, "🔮 Sehrli oynangiz o'qni qaytardi! Siz omon qoldingiz.")
                await bot.send_message(
                    game.chat_id,
                    f"🔮 Tun natijasi: mafiyaning o'qi qaytib, <b>{mention(bounced)}</b> halok bo'ldi.\n"
                    f"U — {ROLE_NAMES[bounced.role]} edi.",
                )
                mafia_resolved = True
            else:
                victim_id = None

    if rifle_used:
        for uid in list(game.mafia_rifle_users):
            if await db.consume_item(uid, "rifle"):
                shooter = game.players.get(uid)
                if shooter:
                    shooter.items["rifle"] = max(0, shooter.items.get("rifle", 0) - 1)

    if not mafia_resolved and victim_id is not None:
        victim = game.players[victim_id]

        if not rifle_used and victim.items.get("shield", 0) > 0 and await db.consume_item(victim.user_id, "shield"):
            victim.items["shield"] -= 1
            await _safe_send(bot, victim.user_id, "🛡 Himoyangiz sizni mafiya hujumidan saqlab qoldi!")
        else:
            victim.alive = False
            tonight_deaths.add(victim.user_id)
            await bot.send_message(
                game.chat_id,
                f"☠️ Tun natijasi: <b>{mention(victim)}</b> halok bo'ldi.\n"
                f"U — {ROLE_NAMES[victim.role]} edi.",
            )

    # Qotil — mustaqil o'ldirish.
    if game.killer_target is not None:
        kvictim = game.players.get(game.killer_target)
        if kvictim and kvictim.alive:
            if kvictim.items.get("killer_shield", 0) > 0:
                await _safe_send(bot, kvictim.user_id, "⛑ Qotildan himoyangiz sizni saqlab qoldi!")
            else:
                kvictim.alive = False
                tonight_deaths.add(kvictim.user_id)
                await bot.send_message(
                    game.chat_id,
                    f"🔪 Tun natijasi: <b>{mention(kvictim)}</b> noma'lum qotil tomonidan halok bo'ldi.\n"
                    f"U — {ROLE_NAMES[kvictim.role]} edi.",
                )

    # Yollanma qotil — mustaqil o'ldirish + buyurtma bonusi.
    if game.hitman_target is not None:
        hvictim = game.players.get(game.hitman_target)
        hitman_player = next((p for p in game.players.values() if p.alive and p.role == Role.HITMAN), None)
        if hvictim and hvictim.alive:
            if hvictim.items.get("killer_shield", 0) > 0:
                await _safe_send(bot, hvictim.user_id, "⛑ Qotildan himoyangiz sizni saqlab qoldi!")
            else:
                hvictim.alive = False
                tonight_deaths.add(hvictim.user_id)
                await bot.send_message(
                    game.chat_id,
                    f"🥷 Tun natijasi: <b>{mention(hvictim)}</b> yollanma qotil tomonidan halok bo'ldi.\n"
                    f"U — {ROLE_NAMES[hvictim.role]} edi.",
                )
                if hitman_player and hitman_player.contract_target == hvictim.user_id:
                    await db.add_balance(hitman_player.user_id, dollars=HITMAN_CONTRACT_BONUS_DOLLARS)
                    await _safe_send(
                        bot,
                        hitman_player.user_id,
                        f"🎯 Buyurtmangizni bajardingiz! +{HITMAN_CONTRACT_BONUS_DOLLARS}💵 bonus oldingiz.",
                    )

    # Konchi — passiv sirg'anish xavfi.
    for miner in [p for p in game.players.values() if p.alive and p.role == Role.MINER]:
        if random.random() >= MINER_SLIP_CHANCE:
            continue
        if miner.items.get("miner_shield", 0) > 0 and await db.consume_item(miner.user_id, "miner_shield"):
            miner.items["miner_shield"] -= 1
            await _safe_send(bot, miner.user_id, "🪤 Sirpanishdan himoyangiz sizni saqlab qoldi!")
        else:
            miner.alive = False
            tonight_deaths.add(miner.user_id)
            await bot.send_message(
                game.chat_id,
                f"⛏ Tun natijasi: <b>{mention(miner)}</b> sirg'anib halok bo'ldi.\n"
                f"U — {ROLE_NAMES[miner.role]} edi.",
            )

    # Daydi — tashrif natijasi.
    if game.wanderer_target in tonight_deaths:
        wanderer_player = next((p for p in game.players.values() if p.alive and p.role == Role.WANDERER), None)
        visited = game.players.get(game.wanderer_target)
        if wanderer_player and visited:
            if visited.items.get("mask", 0) > 0 and await db.consume_item(visited.user_id, "mask"):
                visited.items["mask"] -= 1
            else:
                await _safe_send(
                    bot,
                    wanderer_player.user_id,
                    f"🚶 Siz tashrif buyurgan {visited.full_name} shu kecha halok bo'lganini bilib oldingiz.",
                )

    if not tonight_deaths:
        await bot.send_message(game.chat_id, "🌤 Tun tinch o'tdi. Bu safar hech kim halok bo'lmadi.")


async def dawn_phase(bot: Bot, game: Game) -> None:
    eligible = [p for p in game.players.values() if p.alive and p.items.get("hero_shot", 0) > 0]
    if not eligible:
        return

    game.state = GameState.DAWN
    game.dawn_shots.clear()
    game.dawn_acted.clear()
    game.dawn_needed = len(eligible)
    game.dawn_event = asyncio.Event()

    for hero in eligible:
        kb = build_target_keyboard(game, exclude_ids={hero.user_id}, prefix="hero_shot")
        await _safe_send(
            bot,
            hero.user_id,
            "🥷 Sizda Geroy buyumi bor — tongda bir marta otish huquqingiz bor! "
            "Kimni otmoqchisiz? (xohlamasangiz e'tiborsiz qoldiring)",
            reply_markup=kb,
        )

    try:
        await asyncio.wait_for(game.dawn_event.wait(), timeout=DAWN_DURATION)
    except asyncio.TimeoutError:
        pass

    for shooter_id, target_id in list(game.dawn_shots.items()):
        shooter = game.players.get(shooter_id)
        target = game.players.get(target_id)
        if not shooter or not target or not target.alive:
            continue
        if not await db.consume_item(shooter_id, "hero_shot"):
            continue
        shooter.items["hero_shot"] = max(0, shooter.items.get("hero_shot", 0) - 1)

        if target.items.get("hero_immunity", 0) > 0 and await db.consume_item(target.user_id, "hero_immunity"):
            target.items["hero_immunity"] -= 1
            continue

        target.alive = False
        await bot.send_message(
            game.chat_id,
            f"🥷 Tong otishi: <b>{mention(target)}</b> halok bo'ldi.\n"
            f"U — {ROLE_NAMES[target.role]} edi.",
        )


async def day_phase(bot: Bot, game: Game) -> None:
    game.state = GameState.DAY_DISCUSSION
    alive = [p for p in game.players.values() if p.alive]
    await _send_phase_image(
        bot,
        game.chat_id,
        DAY_IMAGE_PATH,
        "day",
        f"🌅 <b>Xayrli tong!</b>\n☀️ Kun: {game.day_number}\n"
        "Shamollar tundagi mish-mishlarni butun shaharga yetkazmoqda..",
    )

    username = await _get_bot_username(bot)
    await bot.send_message(
        game.chat_id,
        f"👥 <b>Tirik o'yinchilar:</b>\n{_alive_list_text(game)}\n\n"
        f"⏳ Muhokama tugashiga {DAY_DISCUSSION_DURATION} soniya qoldi.",
        reply_markup=_goto_bot_keyboard(username),
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
    elif winner == "killer":
        lines.append("🔪 <b>Qotil yakka o'zi g'alaba qozondi!</b> Shaharda faqat u qoldi.")
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

            await dawn_phase(bot, game)
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
