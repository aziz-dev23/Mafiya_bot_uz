import asyncio
import logging
import random
import time
from collections import Counter
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

import db
from config import DAWN_DURATION, DAY_DISCUSSION_DURATION, NIGHT_DURATION, REVENGE_DURATION, VOTE_DURATION
from economy import HERO_BYPASS_LEVEL, HERO_ELIGIBLE_ROLES, HITMAN_CONTRACT_BONUS_DOLLARS, payout_game_results
from texts import ROLE_NAMES
from utils import (
    build_don_check_keyboard,
    build_mafia_kill_keyboard,
    build_target_keyboard,
    build_vote_keyboard,
    mention,
)

from .manager import manager
from .models import Game, GameState, Player, Role

logger = logging.getLogger(__name__)

MAFIA_KILL_ROLES = (Role.MAFIA, Role.DON)
MAFIA_TEAM_ROLES = (Role.MAFIA, Role.DON, Role.LAWYER, Role.HITMAN)
NIGHT_RESULTS_DELAY = 20

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
DAY_IMAGE_PATH = ASSETS_DIR / "day.jpg"
NIGHT_IMAGE_PATH = ASSETS_DIR / "night.jpg"
ROUND_TABLE_IMAGE_PATH = ASSETS_DIR / "round_table.jpg"
_PHASE_IMAGE_CACHE: dict[str, str] = {}
_BOT_USERNAME_CACHE: str | None = None


async def send_phase_image(
    bot: Bot,
    chat_id: int,
    path: Path,
    cache_key: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Sends a banner/card image as a photo; caches the Telegram file_id after the first upload."""
    try:
        photo = _PHASE_IMAGE_CACHE.get(cache_key) or FSInputFile(path)
        msg = await bot.send_photo(chat_id, photo=photo, caption=caption, reply_markup=reply_markup)
        if cache_key not in _PHASE_IMAGE_CACHE and msg.photo:
            _PHASE_IMAGE_CACHE[cache_key] = msg.photo[-1].file_id
    except (TelegramBadRequest, TelegramForbiddenError, FileNotFoundError):
        await bot.send_message(chat_id, caption, reply_markup=reply_markup)


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
    if game.night_advokat_needed and not game.advokat_acted:
        return False
    return True


async def _safe_send(bot: Bot, user_id: int, text: str, **kwargs) -> None:
    try:
        await bot.send_message(user_id, text, **kwargs)
    except (TelegramForbiddenError, TelegramBadRequest):
        pass


async def _safe_send_replace(bot: Bot, game: Game, user_id: int, text: str, **kwargs) -> None:
    """Shaxsiy chatda avvalgi so'rov xabarini o'chirib, o'rniga yangisini yuboradi —
    shu orqali eski (tugmali) xabarlar har kecha/kun to'planib qolmaydi."""
    old_msg_id = game.last_action_msg.pop(user_id, None)
    if old_msg_id is not None:
        try:
            await bot.delete_message(user_id, old_msg_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass

    try:
        msg = await bot.send_message(user_id, text, **kwargs)
    except (TelegramForbiddenError, TelegramBadRequest):
        return
    game.last_action_msg[user_id] = msg.message_id


async def _kill_player(bot: Bot, game: Game, player: Player) -> None:
    """O'yinchini halok qiladi; agar u Don bo'lsa, tirik mafiyalardan biri yangi Don bo'ladi."""
    player.alive = False
    if player.role != Role.DON:
        return

    successors = [p for p in game.players.values() if p.alive and p.role == Role.MAFIA]
    if not successors:
        return
    new_don = random.choice(successors)
    new_don.role = Role.DON
    await _safe_send(
        bot, new_don.user_id, "🤵🏻 Don halok bo'ldi! Mafiya jamoasi ichida endi siz — yangi Donsiz."
    )


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
    game.advokat_target = None
    game.advokat_acted = False
    game.night_event = asyncio.Event()

    tonight_deaths: set[int] = set()

    # O'tgan tundagi Kezuvchi dorisi shu kecha ta'sir qiladi (agar bor bo'lsa).
    for victim_id, die_night in list(game.pending_poison.items()):
        if die_night != game.day_number:
            continue
        del game.pending_poison[victim_id]
        victim = game.players.get(victim_id)
        if victim and victim.alive:
            await _kill_player(bot, game, victim)
            tonight_deaths.add(victim.user_id)
            await bot.send_message(
                game.chat_id,
                f"💊 Tun natijasi: <b>{mention(victim)}</b> kezuvchining dorisidan halok bo'ldi.\n"
                f"U — {ROLE_NAMES[victim.role]} edi.",
            )

    alive_mafia = [p for p in game.players.values() if p.alive and p.role in MAFIA_KILL_ROLES]
    alive_doctor = [p for p in game.players.values() if p.alive and p.role == Role.DOCTOR]
    alive_detective = [p for p in game.players.values() if p.alive and p.role == Role.DETECTIVE]
    alive_killer = [p for p in game.players.values() if p.alive and p.role == Role.KILLER]
    alive_hitman = [p for p in game.players.values() if p.alive and p.role == Role.HITMAN]
    alive_poisoner = [p for p in game.players.values() if p.alive and p.role == Role.POISONER]
    alive_wanderer = [p for p in game.players.values() if p.alive and p.role == Role.WANDERER]
    alive_don = [p for p in game.players.values() if p.alive and p.role == Role.DON]
    alive_advokat = [p for p in game.players.values() if p.alive and p.role == Role.LAWYER]

    game.night_mafia_needed = len(alive_mafia)
    game.night_doctor_needed = bool(alive_doctor)
    game.night_detective_needed = bool(alive_detective)
    game.night_killer_needed = bool(alive_killer)
    game.night_hitman_needed = bool(alive_hitman)
    game.night_poisoner_needed = bool(alive_poisoner)
    game.night_wanderer_needed = bool(alive_wanderer)
    game.night_advokat_needed = bool(alive_advokat)

    await send_phase_image(
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
    night_prompt_tasks = []

    for m in alive_mafia:
        teammates = ", ".join(p.full_name for p in alive_mafia if p.user_id != m.user_id) or "yo'q"
        kb = build_mafia_kill_keyboard(game, m.user_id, exclude_ids=mafia_ids)
        night_prompt_tasks.append(
            _safe_send_replace(
                bot,
                game,
                m.user_id,
                f"🔪 Kimni yo'q qilmoqchisiz?\nSherik mafiyalar: {teammates}",
                reply_markup=kb,
            )
        )

    for d in alive_doctor:
        kb = build_target_keyboard(game, exclude_ids=set(), prefix="d_save")
        night_prompt_tasks.append(
            _safe_send_replace(bot, game, d.user_id, "💊 Kimni himoya qilmoqchisiz?", reply_markup=kb)
        )

    for c in alive_detective:
        kb = build_target_keyboard(game, exclude_ids={c.user_id}, prefix="c_check")
        night_prompt_tasks.append(
            _safe_send_replace(bot, game, c.user_id, "🕵️ Kimni tekshirmoqchisiz?", reply_markup=kb)
        )

    for k in alive_killer:
        kb = build_target_keyboard(game, exclude_ids={k.user_id}, prefix="q_kill")
        night_prompt_tasks.append(
            _safe_send_replace(bot, game, k.user_id, "🔪 Kimni yo'q qilmoqchisiz? (mustaqil)", reply_markup=kb)
        )

    for h in alive_hitman:
        kb = build_target_keyboard(game, exclude_ids={h.user_id}, prefix="yq_kill")
        night_prompt_tasks.append(
            _safe_send_replace(bot, game, h.user_id, "🥷 Kimni yo'q qilmoqchisiz? (mustaqil)", reply_markup=kb)
        )

    for p_ in alive_poisoner:
        kb = build_target_keyboard(game, exclude_ids={p_.user_id}, prefix="kez_dose")
        night_prompt_tasks.append(
            _safe_send_replace(bot, game, p_.user_id, "💊 Kimga dori bermoqchisiz?", reply_markup=kb)
        )

    for w in alive_wanderer:
        kb = build_target_keyboard(game, exclude_ids={w.user_id}, prefix="daydi_visit")
        night_prompt_tasks.append(
            _safe_send_replace(bot, game, w.user_id, "🚶 Kimning oldiga bormoqchisiz?", reply_markup=kb)
        )

    for don in alive_don:
        if game.don_check_used:
            continue
        kb = build_don_check_keyboard(game, exclude_ids=mafia_ids)
        night_prompt_tasks.append(
            _safe_send_replace(
                bot,
                game,
                don.user_id,
                "🎩 Xohlasangiz, kimningdir Komissar ekanini aniqlashga urinib ko'rishingiz mumkin "
                "(butun o'yin davomida faqat bir marta):",
                reply_markup=kb,
            )
        )

    for law in alive_advokat:
        kb = build_target_keyboard(game, exclude_ids={law.user_id}, prefix="advokat_shield")
        night_prompt_tasks.append(
            _safe_send_replace(
                bot, game, law.user_id, "👨‍💼 Kimni tekshiruvdan (Komissardan) himoya qilmoqchisiz?", reply_markup=kb
            )
        )

    if night_prompt_tasks:
        await asyncio.gather(*night_prompt_tasks)

    if night_all_done(game):
        game.night_event.set()

    try:
        await asyncio.wait_for(game.night_event.wait(), timeout=NIGHT_DURATION)
    except asyncio.TimeoutError:
        pass

    # Barcha tungi harakatlar yig'ilgach, natijalar e'lon qilinishidan oldin taranglik uchun kutamiz.
    await asyncio.sleep(NIGHT_RESULTS_DELAY)

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

    if victim_id is not None and game.players[victim_id].role == Role.WOLF:
        wolf = game.players[victim_id]
        wolf.role = Role.MAFIA
        await _safe_send(
            bot,
            wolf.user_id,
            "🐺 Mafiya sizni tunda yo'q qilishga urindi... lekin siz aslida ulardan ekansiz! "
            "Siz endi Mafiya jamoasining a'zosisiz.",
        )
        victim_id = None
        mafia_resolved = True

    if victim_id is not None:
        victim = game.players[victim_id]

        if victim.items.get("mirror", 0) > 0 and await db.consume_item(victim.user_id, "mirror"):
            victim.items["mirror"] -= 1
            alive_mafia_ids = [p.user_id for p in game.players.values() if p.alive and p.role in MAFIA_TEAM_ROLES]
            if alive_mafia_ids:
                bounced = game.players[random.choice(alive_mafia_ids)]
                await _kill_player(bot, game, bounced)
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

        if (
            not rifle_used
            and not victim.shield_used
            and victim.items.get("shield", 0) > 0
            and await db.consume_item(victim.user_id, "shield")
        ):
            victim.items["shield"] -= 1
            victim.shield_used = True
            await _safe_send(bot, victim.user_id, "🛡 Himoyangiz sizni mafiya hujumidan saqlab qoldi! (bu o'yinda yana ishlamaydi)")
        else:
            await _kill_player(bot, game, victim)
            tonight_deaths.add(victim.user_id)
            await bot.send_message(
                game.chat_id,
                f"☠️ Tun natijasi: <b>{mention(victim)}</b> halok bo'ldi.\n"
                f"U — {ROLE_NAMES[victim.role]} edi.",
            )

            if victim.role == Role.SORCERER:
                drag_pool = [p for p in game.players.values() if p.alive and p.role in MAFIA_TEAM_ROLES]
                if drag_pool:
                    dragged = random.choice(drag_pool)
                    await _kill_player(bot, game, dragged)
                    tonight_deaths.add(dragged.user_id)
                    await bot.send_message(
                        game.chat_id,
                        f"🧞‍♂️ Afsungar o'limidan oldin <b>{mention(dragged)}</b>ni ham o'zi bilan "
                        "olib ketdi!\n"
                        f"U — {ROLE_NAMES[dragged.role]} edi.",
                    )

    # Qotil — mustaqil o'ldirish.
    if game.killer_target is not None:
        kvictim = game.players.get(game.killer_target)
        if kvictim and kvictim.alive:
            if kvictim.items.get("killer_shield", 0) > 0:
                await _safe_send(bot, kvictim.user_id, "⛑ Qotildan himoyangiz sizni saqlab qoldi!")
            else:
                await _kill_player(bot, game, kvictim)
                tonight_deaths.add(kvictim.user_id)
                await bot.send_message(
                    game.chat_id,
                    f"🔪 Tun natijasi: <b>{mention(kvictim)}</b> noma'lum qotil tomonidan halok bo'ldi.\n"
                    f"U — {ROLE_NAMES[kvictim.role]} edi.",
                )

    # Yollanma qotil — mafiya tarafida o'ldiradi, o'z buyurtma bonusi bilan.
    if game.hitman_target is not None:
        hvictim = game.players.get(game.hitman_target)
        hitman_player = next((p for p in game.players.values() if p.alive and p.role == Role.HITMAN), None)
        if hvictim and hvictim.alive:
            if hvictim.items.get("killer_shield", 0) > 0:
                await _safe_send(bot, hvictim.user_id, "⛑ Qotildan himoyangiz sizni saqlab qoldi!")
            else:
                await _kill_player(bot, game, hvictim)
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
    eligible = [
        p for p in game.players.values() if p.alive and p.hero_level > 0 and p.role in HERO_ELIGIBLE_ROLES
    ]
    if not eligible:
        return

    game.state = GameState.DAWN
    game.dawn_shots.clear()
    game.dawn_acted.clear()
    game.dawn_needed = len(eligible)
    game.dawn_event = asyncio.Event()

    dawn_prompt_tasks = [
        _safe_send_replace(
            bot,
            game,
            hero.user_id,
            "🦸 Siz Geroysiz — tongda zarba berish huquqingiz bor! "
            "Kimni otmoqchisiz? (xohlamasangiz e'tiborsiz qoldiring)",
            reply_markup=build_target_keyboard(game, exclude_ids={hero.user_id}, prefix="hero_shot"),
        )
        for hero in eligible
    ]
    await asyncio.gather(*dawn_prompt_tasks)

    try:
        await asyncio.wait_for(game.dawn_event.wait(), timeout=DAWN_DURATION)
    except asyncio.TimeoutError:
        pass

    for shooter_id, target_id in list(game.dawn_shots.items()):
        shooter = game.players.get(shooter_id)
        target = game.players.get(target_id)
        if not shooter or not shooter.alive or not target or not target.alive:
            continue

        bypass_all = shooter.hero_level >= HERO_BYPASS_LEVEL
        if not bypass_all:
            if target.items.get("mirror", 0) > 0 and await db.consume_item(target.user_id, "mirror"):
                target.items["mirror"] -= 1
                await _safe_send(bot, shooter.user_id, "🔮 Nishoningizning sehrli oynasi zarbangizni qaytardi!")
                await _safe_send(bot, target.user_id, "🔮 Sehrli oynangiz Geroy zarbasidan sizni asradi!")
                continue
            if target.items.get("hero_immunity", 0) > 0 and await db.consume_item(target.user_id, "hero_immunity"):
                target.items["hero_immunity"] -= 1
                await _safe_send(bot, target.user_id, "🔰 Geroydan himoyangiz sizni zarbadan asradi!")
                continue

        await _kill_player(bot, game, target)
        await bot.send_message(
            game.chat_id,
            f"🦸 Geroy zarbasi: <b>{mention(target)}</b> halok bo'ldi.\n"
            f"U — {ROLE_NAMES[target.role]} edi.",
        )


async def _resolve_sorcerer_revenge(bot: Bot, game: Game, sorcerer) -> None:
    others = [p for p in game.players.values() if p.alive and p.user_id != sorcerer.user_id]
    if not others:
        return

    await bot.send_message(game.chat_id, "🧞‍♂️ Lekin Afsungar so'nggi so'zini aytishga ulguradi...")

    game.revenge_target = None
    game.revenge_event = asyncio.Event()
    kb = build_target_keyboard(game, exclude_ids={sorcerer.user_id}, prefix="sorcerer_revenge")
    await _safe_send(bot, sorcerer.user_id, "🧞‍♂️ O'limingizdan oldin kimdan o'ch olmoqchisiz?", reply_markup=kb)

    try:
        await asyncio.wait_for(game.revenge_event.wait(), timeout=REVENGE_DURATION)
    except asyncio.TimeoutError:
        pass

    if game.revenge_target is not None:
        target = game.players.get(game.revenge_target)
        if target and target.alive:
            await _kill_player(bot, game, target)
            await bot.send_message(
                game.chat_id,
                f"🧞‍♂️ Afsungarning o'chi: <b>{mention(target)}</b> ham halok bo'ldi!\n"
                f"U — {ROLE_NAMES[target.role]} edi.",
            )


async def day_phase(bot: Bot, game: Game) -> None:
    game.state = GameState.DAY_DISCUSSION
    alive = [p for p in game.players.values() if p.alive]
    await send_phase_image(
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

    await bot.send_message(
        game.chat_id,
        "🗳 <b>Ovoz berish boshlandi!</b>\nHar bir o'yinchi ovozini shaxsiy xabarda beradi.\n"
        f"⏳ {VOTE_DURATION} soniya vaqt bor.",
        reply_markup=_goto_bot_keyboard(username),
    )

    kb = build_vote_keyboard(game)
    vote_prompt_tasks = [
        _safe_send_replace(bot, game, voter.user_id, "🗳 Kimni shahardan haydab chiqarmoqchisiz?", reply_markup=kb)
        for voter in alive
    ]
    await asyncio.gather(*vote_prompt_tasks)

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

                await _kill_player(bot, game, eliminated)
                await bot.send_message(
                    game.chat_id,
                    f"⚖️ Shahar ovoz berdi: <b>{mention(eliminated)}</b> haydab "
                    f"chiqarildi.\nU — {ROLE_NAMES[eliminated.role]} edi.",
                )

                if eliminated.role == Role.SORCERER:
                    await _resolve_sorcerer_revenge(bot, game, eliminated)
                return

    await bot.send_message(game.chat_id, "⚖️ Ovozlar teng bo'ldi yoki hech kim ovoz bermadi — bugun hech kim haydalmadi.")


def _is_winner_role(role: Role, winner: str) -> bool:
    if winner == "killer":
        return role == Role.KILLER
    if winner == "mafia":
        return role in MAFIA_TEAM_ROLES
    return role not in MAFIA_TEAM_ROLES and role != Role.KILLER


async def finish_game(bot: Bot, game: Game, winner: str) -> None:
    game.state = GameState.FINISHED
    if winner == "town":
        result_text = "🎉 <b>Tinch aholi g'alaba qozondi!</b> Barcha mafiyalar tutildi."
    elif winner == "killer":
        result_text = "🔪 <b>Qotil yakka o'zi g'alaba qozondi!</b> Shaharda faqat u qoldi."
    else:
        result_text = "🔪 <b>Mafiya g'alaba qozondi!</b> Shahar ularning qo'liga o'tdi."

    private_messages = await payout_game_results(game, winner)
    for user_id, text in private_messages:
        await _safe_send(bot, user_id, f"🏁 <b>O'yin tugadi!</b>\n\n{result_text}\n\n{text}")

    winners = [p for p in game.players.values() if _is_winner_role(p.role, winner)]
    losers = [p for p in game.players.values() if not _is_winner_role(p.role, winner)]

    lines = ["🏁 <b>O'yin tugadi!</b>", "", result_text, ""]

    idx = 1
    lines.append("<b>G'oliblar:</b>")
    for p in winners:
        lines.append(f"{idx}. {p.full_name} — {ROLE_NAMES[p.role]}")
        idx += 1

    if losers:
        lines.append("")
        lines.append("<b>Qolgan o'yinchilar:</b>")
        for p in losers:
            lines.append(f"{idx}. {p.full_name} — {ROLE_NAMES[p.role]}")
            idx += 1

    elapsed_min = max(1, round((time.time() - game.started_at) / 60)) if game.started_at else 0
    lines.append("")
    lines.append(f"⏱ O'yin: {elapsed_min} daqiqa davom etdi")
    lines.append("")
    lines.append("🏅 Reyting uchun: /top (jami), /top1 (kunlik), /top7 (haftalik)")

    await bot.send_message(game.chat_id, "\n".join(lines))
    manager.remove_game(game.chat_id)


async def run_game(bot: Bot, game: Game) -> None:
    game.task = asyncio.current_task()
    game.started_at = time.time()
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
