import asyncio
import logging
import random
import time
from collections import Counter
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from config import AFK_LIMIT, ANNOUNCE_BATCH_DELAY, LAST_WORD_MAX_LENGTH, REMINDER_BEFORE_END
from economy import (
    GUESS_REWARD_COINS,
    HERO_BYPASS_LEVEL,
    HERO_ELIGIBLE_ROLES,
    HITMAN_CONTRACT_BONUS_DOLLARS,
    ITEMS,
    MINER_COIN_CHANCE,
    MINER_COIN_MAX,
    MINER_COIN_MIN,
    MINER_ITEM_CHANCE,
    MINER_ITEM_POOL,
    MVP_DOCTOR_SAVE,
    MVP_HITMAN_CONTRACT,
    MVP_MAFIA_KILL_VOTE,
    MVP_SORCERER_DRAG,
    MVP_VOTED_OUT_MAFIA,
    MVP_WANDERER_SAW_KILLER,
    POISONER_MAX_USES,
    add_mvp,
    did_win,
    payout_game_results,
)
from i18n import get_texts
from utils import (
    build_confirm_keyboard,
    build_don_check_keyboard,
    build_mafia_kill_keyboard,
    build_target_keyboard,
    build_vote_keyboard,
    esc,
    hero_badge,
    mention,
    split_text,
)

from .chatlock import lock_chat, unlock_chat
from .manager import manager
from .models import MAFIA_KILL_ROLES, MAFIA_TEAM_ROLES, Game, GameState, Player, Role
from .settings import LOCK_ALL

logger = logging.getLogger(__name__)

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


def gt(game: Game):
    """Guruhga chiqadigan matnlar — guruh tilida."""
    return get_texts(game.settings.lang)


def pt(player: Player):
    """Shaxsiy matnlar — o'yinchining o'z tilida."""
    return get_texts(player.lang)


def _goto_bot_keyboard(game: Game, username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=gt(game).GOTO_BOT_BUTTON, url=f"https://t.me/{username}")]]
    )


def _alive_list_text(game: Game) -> str:
    alive = [p for p in game.players.values() if p.alive]
    return "\n".join(f"{i}. {esc(p.full_name)}" for i, p in enumerate(alive, 1))


def _alive(game: Game, *roles: Role) -> list[Player]:
    return [p for p in game.players.values() if p.alive and (not roles or p.role in roles)]


def _secs(value: float) -> int:
    return max(1, round(value))


async def _wait_with_reminder(event: asyncio.Event, total: float, remind) -> None:
    """event ni ko'pi bilan total soniya kutadi; tugashiga REMINDER_BEFORE_END soniya qolganda
    (hali tugamagan bo'lsa) remind() chaqiriladi."""
    first = total - REMINDER_BEFORE_END
    if first > 0:
        try:
            await asyncio.wait_for(event.wait(), timeout=first)
            return
        except asyncio.TimeoutError:
            pass
        await remind()
    try:
        await asyncio.wait_for(event.wait(), timeout=min(total, REMINDER_BEFORE_END))
    except asyncio.TimeoutError:
        pass


# ---------- O'yin tarixi ----------


def log(game: Game, line: str) -> None:
    game.history.append(line)


def _n(player: Player | None) -> str:
    return esc(player.full_name) if player else "?"


def role_reveal(game: Game, player: Player) -> str:
    """O'lgan o'yinchining roli — faqat guruh sozlamasida rol e'loni yoqilgan bo'lsa."""
    L = gt(game)
    return L.ROLE_REVEAL.format(role=L.ROLE_NAMES[player.role]) if game.settings.reveal_roles else ""


# ---------- Xabar yuborish yordamchilari ----------


async def _safe_send(bot: Bot, user_id: int, text: str, **kwargs) -> Message | None:
    try:
        return await bot.send_message(user_id, text, **kwargs)
    except (TelegramForbiddenError, TelegramBadRequest):
        return None


async def _safe_send_replace(bot: Bot, game: Game, user_id: int, text: str, **kwargs) -> None:
    """Shaxsiy chatda avvalgi so'rov xabarini o'chirib, o'rniga yangisini yuboradi —
    shu orqali eski (tugmali) xabarlar har kecha/kun to'planib qolmaydi."""
    old_msg_id = game.last_action_msg.pop(user_id, None)
    if old_msg_id is not None:
        try:
            await bot.delete_message(user_id, old_msg_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass

    msg = await _safe_send(bot, user_id, text, **kwargs)
    if msg is not None:
        game.last_action_msg[user_id] = msg.message_id


async def _send_group(bot: Bot, game: Game, text: str) -> None:
    for part in split_text(text):
        try:
            await bot.send_message(game.chat_id, part)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass


def announce(bot: Bot, game: Game, text: str) -> None:
    """Qisqa guruh e'lonini navbatga qo'yadi: ANNOUNCE_BATCH_DELAY soniya ichidagi e'lonlar
    bitta xabar bo'lib chiqadi (guruhga daqiqasiga 20 ta xabar limiti uchun)."""
    game.announce_buffer.append(text)
    if game.announce_task is None or game.announce_task.done():
        game.announce_task = asyncio.create_task(_delayed_flush(bot, game))


async def _delayed_flush(bot: Bot, game: Game) -> None:
    await asyncio.sleep(ANNOUNCE_BATCH_DELAY)
    game.announce_task = None
    await _send_buffer(bot, game)


async def _send_buffer(bot: Bot, game: Game) -> None:
    if not game.announce_buffer:
        return
    text = "\n".join(game.announce_buffer)
    game.announce_buffer.clear()
    await _send_group(bot, game, text)


async def flush_announcements(bot: Bot, game: Game) -> None:
    """Navbatdagi e'lonlarni darhol yuboradi (bosqich yakunidagi xabarlardan oldin, tartib buzilmasligi uchun)."""
    task = game.announce_task
    game.announce_task = None
    if task and not task.done() and task is not asyncio.current_task():
        task.cancel()
    await _send_buffer(bot, game)


async def _report(bot: Bot, game: Game, line: str) -> None:
    """Tunda — natijalar ro'yxatiga (tun oxirida bitta xabar bo'lib chiqadi), boshqa paytda — darhol guruhga."""
    if game.state == GameState.NIGHT:
        game.night_results.append(line)
    else:
        await _send_group(bot, game, line)


def _death_line(game: Game, prefix: str, player: Player) -> str:
    return gt(game).DEATH_LINE.format(prefix=prefix, name=mention(player), role=role_reveal(game, player))


# ---------- O'lim va g'alaba ----------


async def _kill_player(bot: Bot, game: Game, player: Player, last_word: bool = True) -> None:
    """O'yinchini halok qiladi va o'limning oqibatlarini hal qiladi:
    Don o'lsa — tirik Mafiyalardan biri yangi Don; Komissar o'lsa — Serjant yangi Komissar;
    oshiqlardan biri o'lsa — ikkinchisi ham halok bo'ladi. So'nggi so'z imkoniyati beriladi."""
    player.alive = False
    log(game, gt(game).H_DEATH.format(name=_n(player), role=gt(game).ROLE_NAMES[player.role]))
    P = pt(player)
    if last_word and game.settings.last_word:
        seconds = game.settings.seconds("last_word")
        game.last_word_deadline[player.user_id] = time.monotonic() + seconds
        await _safe_send(
            bot, player.user_id, P.LAST_WORD_PROMPT.format(seconds=_secs(seconds), limit=LAST_WORD_MAX_LENGTH)
        )
    await _safe_send(bot, player.user_id, P.DEAD_CHAT_HINT)

    if player.role == Role.DON:
        successors = _alive(game, Role.MAFIA)
        if successors:
            new_don = random.choice(successors)
            new_don.role = Role.DON
            await _safe_send(bot, new_don.user_id, pt(new_don).NEW_DON)

    if player.role == Role.DETECTIVE and not _alive(game, Role.DETECTIVE):
        sergeants = _alive(game, Role.SERGEANT)
        if sergeants:
            sergeants[0].role = Role.DETECTIVE
            await _safe_send(bot, sergeants[0].user_id, pt(sergeants[0]).SERGEANT_PROMOTED)

    if game.lovers and player.user_id in game.lovers:
        partner_id = game.lovers[1] if game.lovers[0] == player.user_id else game.lovers[0]
        partner = game.players.get(partner_id)
        if partner and partner.alive:
            await _kill_player(bot, game, partner)
            if game.state == GameState.NIGHT:
                game.night_kills.setdefault(partner.user_id, None)
            await _report(bot, game, gt(game).LOVER_DIED.format(name=mention(partner), role=role_reveal(game, partner)))


def check_win(game: Game) -> str | None:
    alive_players = _alive(game)
    killer_alive = any(p.role == Role.KILLER for p in alive_players)
    alive_mafia = sum(1 for p in alive_players if p.role in MAFIA_TEAM_ROLES)
    alive_others = sum(1 for p in alive_players if p.role not in MAFIA_TEAM_ROLES)

    # Qotil yolg'iz qolsa yoki Mafiyasiz 1 ga 1 qolsa yutadi (aks holda o'yin cheksiz davom etishi mumkin).
    if killer_alive and alive_mafia == 0 and len(alive_players) <= 2:
        return "killer"
    if alive_mafia == 0:
        # Tinch aholi faqat Mafiya jamoasi ham, Qotil ham yo'q qilinganda yutadi.
        return None if killer_alive else "town"
    if alive_mafia >= alive_others:
        return "mafia"
    return None


def team_of(player: Player) -> str:
    if player.role in MAFIA_TEAM_ROLES:
        return "mafia"
    if player.role == Role.KILLER:
        return "killer"
    return "town"


def _team_names(game: Game, player: Player) -> str:
    names = [esc(p.full_name) for p in _alive(game, *MAFIA_TEAM_ROLES) if p.user_id != player.user_id]
    return ", ".join(names) or pt(player).NO_TEAMMATES


# ---------- Tun ----------


def maybe_end_night(game: Game) -> None:
    """Harakat qilishi kerak bo'lganlarning hammasi harakat qilgan bo'lsa, tunni vaqtidan oldin yakunlaydi."""
    if game.night_event and game.night_expected <= game.night_acted:
        game.night_event.set()


def doctor_forbidden_ids(game: Game, doctor_id: int) -> set[int]:
    """Doktor o'zini o'yinda faqat bir marta va bir odamni ketma-ket ikki kecha himoya qila olmaydi."""
    forbidden = set()
    if doctor_id in game.doctor_self_used:
        forbidden.add(doctor_id)
    if doctor_id in game.doctor_last_target:
        forbidden.add(game.doctor_last_target[doctor_id])
    return forbidden


def mafia_status_text(game: Game, lang: str | None = None) -> str:
    L = get_texts(lang)
    lines = [L.MAFIA_VOTES_HEADER]
    for voter in _alive(game, *MAFIA_KILL_ROLES):
        target_id = game.mafia_votes.get(voter.user_id)
        target = esc(game.players[target_id].full_name) if target_id in game.players else L.MAFIA_VOTE_PENDING
        lines.append(L.MAFIA_VOTE_LINE.format(voter=esc(voter.full_name), target=target))
    return "\n".join(lines)


async def update_mafia_status(bot: Bot, game: Game) -> None:
    """Mafiya jamoasining har bir a'zosidagi ovozlar xabarini tahrirlaydi."""
    for user_id, message_id in list(game.mafia_status_msgs.items()):
        member = game.players.get(user_id)
        text = mafia_status_text(game, member.lang if member else None)
        try:
            await bot.edit_message_text(text, chat_id=user_id, message_id=message_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass


def _reset_night(game: Game) -> None:
    game.state = GameState.NIGHT
    game.night_event = asyncio.Event()
    game.night_expected = set()
    game.night_acted = set()
    game.mafia_votes.clear()
    game.mafia_rifle_users.clear()
    game.mafia_status_msgs.clear()
    game.doctor_targets.clear()
    game.detective_target = None
    game.killer_target = None
    game.hitman_target = None
    game.wanderer_target = None
    game.advokat_target = None
    game.bodyguard_targets.clear()
    game.journalist_first.clear()
    game.cupid_pick.clear()
    game.guesses.clear()
    game.hero_shots.clear()
    game.night_kills.clear()
    game.night_results.clear()


async def night_phase(bot: Bot, game: Game) -> None:
    _reset_night(game)
    G = gt(game)
    log(game, G.HISTORY_NIGHT.format(n=game.day_number))
    if game.settings.lock_mode == LOCK_ALL:
        await lock_chat(bot, game)
    night_seconds = game.settings.seconds("night")

    await send_phase_image(
        bot,
        game.chat_id,
        NIGHT_IMAGE_PATH,
        "night",
        G.NIGHT_BANNER.format(n=game.day_number),
    )

    username = await _get_bot_username(bot)
    await bot.send_message(
        game.chat_id,
        G.ALIVE_LIST.format(players=_alive_list_text(game)) + "\n\n"
        + G.NIGHT_TIME_LEFT.format(seconds=_secs(night_seconds)),
        reply_markup=_goto_bot_keyboard(game, username),
    )

    team_ids = {p.user_id for p in _alive(game, *MAFIA_TEAM_ROLES)}
    prompts: list[tuple[Player, str, InlineKeyboardMarkup]] = []

    def expect(player: Player, text: str, kb: InlineKeyboardMarkup) -> None:
        game.night_expected.add(player.user_id)
        prompts.append((player, text, kb))

    for p in _alive(game):
        uid = p.user_id
        P = pt(p)
        if p.role in MAFIA_KILL_ROLES:
            expect(
                p,
                P.MAFIA_KILL_PROMPT.format(teammates=_team_names(game, p)),
                build_mafia_kill_keyboard(game, uid, exclude_ids=team_ids),
            )
        elif p.role == Role.DOCTOR:
            expect(p, P.DOCTOR_PROMPT, build_target_keyboard(game, doctor_forbidden_ids(game, uid), "d_save"))
        elif p.role == Role.DETECTIVE:
            expect(p, P.DETECTIVE_PROMPT, build_target_keyboard(game, {uid}, "c_check"))
        elif p.role == Role.KILLER:
            expect(p, P.KILLER_PROMPT, build_target_keyboard(game, {uid}, "q_kill"))
        elif p.role == Role.HITMAN:
            expect(
                p,
                P.HITMAN_KILL_PROMPT.format(teammates=_team_names(game, p)),
                build_target_keyboard(game, team_ids, "yq_kill"),
            )
        elif p.role == Role.POISONER and game.poison_uses < POISONER_MAX_USES:
            expect(p, P.POISONER_PROMPT, build_target_keyboard(game, {uid}, "kez_dose"))
        elif p.role == Role.WANDERER:
            expect(p, P.WANDERER_PROMPT, build_target_keyboard(game, {uid}, "daydi_visit"))
        elif p.role == Role.LAWYER:
            expect(
                p,
                P.LAWYER_PROMPT,
                build_target_keyboard(game, {uid}, "advokat_shield"),
            )
        elif p.role == Role.JOURNALIST:
            expect(p, P.JOURNALIST_PROMPT_FIRST, build_target_keyboard(game, {uid}, "jur1"))
        elif p.role == Role.BODYGUARD:
            expect(p, P.BODYGUARD_PROMPT, build_target_keyboard(game, {uid}, "guard"))
        elif p.role == Role.SPY:
            expect(p, P.SPY_PROMPT, build_target_keyboard(game, {uid}, "spy"))
        elif p.role == Role.CUPID and game.lovers is None:
            expect(p, P.CUPID_PROMPT_FIRST, build_target_keyboard(game, set(), "cupid1"))

    # Harakati yo'q tiriklarga — "Bu tun kim o'ladi?" taxmini (ixtiyoriy, tunni ushlab turmaydi).
    guess_tasks = [
        _safe_send_replace(
            bot,
            game,
            p.user_id,
            pt(p).GUESS_PROMPT.format(coins=GUESS_REWARD_COINS),
            reply_markup=build_target_keyboard(game, {p.user_id}, "guess"),
        )
        for p in _alive(game)
        if p.user_id not in game.night_expected
    ]

    prompt_tasks = [_safe_send_replace(bot, game, p.user_id, text, reply_markup=kb) for p, text, kb in prompts]

    # Geroy zarbasi — ixtiyoriy, o'z harakatidan tashqari (tunni ushlab turmaydi).
    for hero in _alive(game):
        if hero_can_shoot(game, hero):
            prompt_tasks.append(
                _safe_send(
                    bot,
                    hero.user_id,
                    pt(hero).HERO_NIGHT_PROMPT,
                    reply_markup=build_target_keyboard(game, {hero.user_id}, "hero_shot"),
                )
            )

    # Don uchun ixtiyoriy tekshiruv (tunni ushlab turmaydi).
    for don in _alive(game, Role.DON):
        if not game.don_check_used:
            prompt_tasks.append(
                _safe_send(
                    bot,
                    don.user_id,
                    pt(don).DON_CHECK_PROMPT,
                    reply_markup=build_don_check_keyboard(game, exclude_ids=team_ids),
                )
            )

    await asyncio.gather(*prompt_tasks, *guess_tasks)
    await _send_mafia_status(bot, game)

    maybe_end_night(game)

    async def remind() -> None:
        for uid in game.night_expected - game.night_acted:
            player = game.players.get(uid)
            if player:
                await _safe_send(bot, uid, pt(player).REMINDER_NIGHT.format(seconds=REMINDER_BEFORE_END))

    await _wait_with_reminder(game.night_event, night_seconds, remind)

    # Barcha tungi harakatlar yig'ilgach, natijalar e'lon qilinishidan oldin taranglik uchun kutamiz.
    await asyncio.sleep(NIGHT_RESULTS_DELAY * game.settings.speed)
    await flush_announcements(bot, game)
    await resolve_night(bot, game)
    await _check_night_afk(bot, game)


async def kick_afk(bot: Bot, game: Game, player: Player) -> None:
    """AFK o'yinchini o'yindan chiqaradi: halok hisoblanadi, roli e'lon qilinadi, mukofot olmaydi."""
    if not player.alive:
        return
    player.afk = True
    log(game, gt(game).H_AFK.format(name=_n(player)))
    await _kill_player(bot, game, player, last_word=False)
    await _send_group(bot, game, gt(game).AFK_KICKED.format(name=mention(player), role=role_reveal(game, player)))
    await _safe_send(bot, player.user_id, pt(player).AFK_KICKED_PRIVATE)


async def _check_night_afk(bot: Bot, game: Game) -> None:
    for uid in game.night_expected:
        player = game.players.get(uid)
        if not player:
            continue
        if uid in game.night_acted:
            player.missed_nights = 0
            continue
        player.missed_nights += 1
        if player.missed_nights >= AFK_LIMIT:
            await kick_afk(bot, game, player)


async def _send_mafia_status(bot: Bot, game: Game) -> None:
    if not _alive(game, *MAFIA_KILL_ROLES):
        return
    for member in _alive(game, *MAFIA_TEAM_ROLES):
        text = f"{mafia_status_text(game, member.lang)}\n\n{pt(member).MAFIA_CHAT_HINT}"
        msg = await _safe_send(bot, member.user_id, text)
        if msg is not None:
            game.mafia_status_msgs[member.user_id] = msg.message_id


def _pick_mafia_target(game: Game) -> int | None:
    """Eng ko'p ovoz olgan nishon; teng bo'lsa — Donning tanlovi, Don tanlamagan bo'lsa — tasodifiy."""
    if not game.mafia_votes:
        return None
    counts = Counter(game.mafia_votes.values())
    max_count = max(counts.values())
    candidates = [uid for uid, c in counts.items() if c == max_count]
    if len(candidates) == 1:
        return candidates[0]
    for don in _alive(game, Role.DON):
        if game.mafia_votes.get(don.user_id) in candidates:
            return game.mafia_votes[don.user_id]
    return random.choice(candidates)


async def use_item(bot: Bot, game: Game, player: Player, key: str) -> bool:
    """O'yinchida shu o'yinda yoqilgan buyum bo'lsa, bir donasini sarflaydi, tarixga yozadi va egasiga
    "Qoldi: N dona" xabarini yuboradi. Buyum faqat natijani haqiqatan o'zgartirganda chaqiriladi."""
    if player.items.get(key, 0) <= 0 or not await db.consume_item(player.user_id, key):
        return False
    player.items[key] -= 1
    G = gt(game)
    log(game, G.H_ITEM.format(emoji=ITEMS[key]["emoji"], owner=_n(player), item=G.ITEM_NAMES[key]))
    left = await db.item_count(player.user_id, key)
    await _safe_send(bot, player.user_id, pt(player).ITEM_USED[key].format(left=left))
    return True


async def _use_rifle(bot: Bot, game: Game, owner: Player) -> bool:
    """🔫 Miltiq /sumka dagi yoqish-o'chirishga bog'liq emas — egasidagi sondan sarflanadi."""
    if owner.rifle_used or owner.rifle_count <= 0 or not await db.consume_item(owner.user_id, "rifle"):
        return False
    owner.rifle_used = True
    owner.rifle_count -= 1
    G = gt(game)
    log(game, G.H_ITEM.format(emoji=ITEMS["rifle"]["emoji"], owner=_n(owner), item=G.ITEM_NAMES["rifle"]))
    left = await db.item_count(owner.user_id, "rifle")
    await _safe_send(bot, owner.user_id, pt(owner).ITEM_USED["rifle"].format(left=left))
    return True


def rifle_available(game: Game, player: Player) -> bool:
    """Miltiq tugmasi: Don/Mafiya, kamida 1 ta Miltiq, "Buyumsiz" rejim emas, shu o'yinda hali ishlatilmagan."""
    return (
        player.role in MAFIA_KILL_ROLES
        and player.rifle_count > 0
        and not player.rifle_used
        and game.settings.items_active
    )


async def _notify_survived(bot: Bot, game: Game, attackers) -> None:
    """Hujumchilarga nishon qaysi sabab bilan omon qolganidan qat'i nazar bir xil xabar."""
    for attacker in attackers:
        if attacker is not None:
            await _safe_send(bot, attacker.user_id, pt(attacker).TARGET_SURVIVED)


async def _bodyguard_intercepts(bot: Bot, game: Game, target: Player, attacker_id: int | None) -> bool:
    """Nishonni tirik Tansoqchi qo'riqlayotgan bo'lsa, zarbani o'ziga oladi (halok bo'ladi)."""
    for guard_id, guarded_id in game.bodyguard_targets.items():
        guard = game.players.get(guard_id)
        if guarded_id == target.user_id and guard and guard.alive:
            await _kill_player(bot, game, guard)
            game.night_kills[guard.user_id] = attacker_id
            await _report(
                bot,
                game,
                gt(game).BODYGUARD_DIED.format(guard=mention(guard), target=esc(target.full_name))
                + role_reveal(game, guard),
            )
            return True
    return False


async def resolve_night(bot: Bot, game: Game) -> None:
    """Tungi harakatlarni hal qiladi. Tartib:
    0) Kupidon juftligi (faqat 1-kecha, o'limlardan oldin — shu kechaning o'zida ham ishlaydi);
    1) Kezuvchi zahari (o'tgan kecha berilgan): Doktor → 💊 Doridan himoya → o'lim;
    2) Mafiya hujumi: Doktor → Bo'ri aylanishi → 🔮 Sehrli oyna → 🛡 Himoya (🔫 Miltiq bo'lmasa)
       → Tansoqchi → o'lim → Afsungar;
    3) Qotil: ⛑ Qotildan himoya → Tansoqchi → o'lim;
    4) Yollanma qotil: ⛑ → Tansoqchi → o'lim (+buyurtma bonusi);
    5) Geroy zarbasi: 🔮 Sehrli oyna → 🔰 Geroydan himoya → o'lim (10+ darajada hech narsa to'xtatmaydi,
       Doktor himoya qilmaydi; nishon shu tunda boshqa sababdan o'lgan bo'lsa, zarba hisobga olinmaydi);
    har bir o'limda: Don/Komissar vorisi, oshiqning ikkinchisi (_kill_player, hech bir buyum ta'sir qilmaydi);
    6) Daydiga natija (qotilda 🎭 Maska bo'lsa — hech narsa ko'rmaydi); 7) Konchi; 8) taxminlar; 9) Doktor cheklovlari.
    Qaytgan o'q (🔮) to'g'ridan-to'g'ri o'ldiradi — unga hech qanday himoya ishlamaydi.
    Komissar (Advokat → 📁 Soxta hujjat), Don, Jurnalist va Josus natijalari tanlov paytida beriladi."""
    G = gt(game)
    doctors_by_target: dict[int, list[int]] = {}
    for doctor_id, target_id in game.doctor_targets.items():
        doctors_by_target.setdefault(target_id, []).append(doctor_id)

    def doctor_saves(target_id: int) -> bool:
        savers = doctors_by_target.get(target_id, [])
        for doctor_id in savers:
            add_mvp(game, doctor_id, MVP_DOCTOR_SAVE)
        return bool(savers)

    _log_night_choices(game)
    await _resolve_cupid(bot, game)

    # 1) Kezuvchi zahari
    poisoner = next((p for p in game.players.values() if p.role == Role.POISONER), None)
    for victim_id, die_night in list(game.pending_poison.items()):
        if die_night != game.day_number:
            continue
        del game.pending_poison[victim_id]
        victim = game.players.get(victim_id)
        if not victim or not victim.alive or doctor_saves(victim_id):
            continue
        if await use_item(bot, game, victim, "poison_shield"):
            continue  # Kezuvchi hech narsa bilmaydi
        await _kill_player(bot, game, victim)
        game.night_kills[victim.user_id] = poisoner.user_id if poisoner else None
        await _report(bot, game, _death_line(game, G.PREFIX_POISON, victim))

    # 2) Mafiya
    mafia_target = _pick_mafia_target(game)
    victim = game.players.get(mafia_target) if mafia_target is not None else None
    if victim and not victim.alive:
        victim = None
    voters = [game.players[uid] for uid, t in game.mafia_votes.items() if victim and t == victim.user_id]
    team = [p for p in _alive(game, *MAFIA_TEAM_ROLES)]

    if victim:
        survived = False
        if doctor_saves(victim.user_id):
            survived = True
        elif victim.role == Role.WOLF:
            # Bo'ri to'liq Mafiya a'zosiga aylanadi: keyingi tundan sheriklarini biladi, chat va ovozda qatnashadi.
            victim.role = Role.MAFIA
            await _safe_send(
                bot, victim.user_id, pt(victim).WOLF_TURNED.format(teammates=_team_names(game, victim))
            )
            survived = True
        elif await use_item(bot, game, victim, "mirror"):
            # O'q nishonga ovoz bergan Don/Mafiyalardan biriga qaytadi va to'g'ridan-to'g'ri o'ldiradi.
            alive_voters = [p for p in voters if p.alive and p.role in MAFIA_KILL_ROLES]
            if alive_voters:
                bounced = random.choice(alive_voters)
                await _kill_player(bot, game, bounced)
                game.night_kills[bounced.user_id] = victim.user_id
                await _report(bot, game, _death_line(game, G.PREFIX_MAFIA, bounced))
            survived = True
        elif victim.items.get("shield", 0) > 0 and not victim.shield_used:
            rifles = [p for p in voters if p.user_id in game.mafia_rifle_users and rifle_available(game, p)]
            don_rifle = next((p for p in rifles if p.role == Role.DON), None)
            rifle_owner = don_rifle or (random.choice(rifles) if rifles else None)
            if rifle_owner is None or not await _use_rifle(bot, game, rifle_owner):
                if await use_item(bot, game, victim, "shield"):
                    victim.shield_used = True
                    survived = True

        if not survived:
            # Shu nishonga ovoz bergan mafiyalardan tasodifiy biri "qotil" hisoblanadi.
            attacker = random.choice(voters).user_id if voters else None
            if await _bodyguard_intercepts(bot, game, victim, attacker):
                survived = True
            else:
                await _kill_player(bot, game, victim)
                game.night_kills[victim.user_id] = attacker
                for voter in voters:
                    add_mvp(game, voter.user_id, MVP_MAFIA_KILL_VOTE)
                await _report(bot, game, _death_line(game, G.PREFIX_MAFIA, victim))

                if victim.role == Role.SORCERER:
                    drag_pool = _alive(game, *MAFIA_TEAM_ROLES)
                    if drag_pool:
                        dragged = random.choice(drag_pool)
                        await _kill_player(bot, game, dragged)
                        game.night_kills[dragged.user_id] = victim.user_id
                        add_mvp(game, victim.user_id, MVP_SORCERER_DRAG)
                        await _report(
                            bot,
                            game,
                            G.SORCERER_DRAGGED.format(name=mention(dragged), role=role_reveal(game, dragged)),
                        )
        if survived:
            await _notify_survived(bot, game, [p for p in team if p.user_id != victim.user_id])

    # 3) Qotil — mustaqil o'ldirish.
    killer_player = next((p for p in game.players.values() if p.role == Role.KILLER), None)
    kvictim = game.players.get(game.killer_target) if game.killer_target is not None else None
    if kvictim and kvictim.alive:
        attacker = killer_player.user_id if killer_player else None
        if await use_item(bot, game, kvictim, "killer_shield") or await _bodyguard_intercepts(
            bot, game, kvictim, attacker
        ):
            await _notify_survived(bot, game, [killer_player])
        else:
            await _kill_player(bot, game, kvictim)
            game.night_kills[kvictim.user_id] = attacker
            await _report(bot, game, _death_line(game, G.PREFIX_KILLER, kvictim))

    # 4) Yollanma qotil — mafiya tarafida o'ldiradi, o'z buyurtma bonusi bilan.
    hitman_player = next((p for p in game.players.values() if p.role == Role.HITMAN), None)
    hvictim = game.players.get(game.hitman_target) if game.hitman_target is not None else None
    if hvictim and hvictim.alive:
        attacker = hitman_player.user_id if hitman_player else None
        if await use_item(bot, game, hvictim, "killer_shield") or await _bodyguard_intercepts(
            bot, game, hvictim, attacker
        ):
            await _notify_survived(bot, game, [hitman_player])
        else:
            await _kill_player(bot, game, hvictim)
            game.night_kills[hvictim.user_id] = attacker
            await _report(bot, game, _death_line(game, G.PREFIX_HITMAN, hvictim))
            if hitman_player and hitman_player.contract_target == hvictim.user_id:
                add_mvp(game, hitman_player.user_id, MVP_HITMAN_CONTRACT)
                await db.add_balance(hitman_player.user_id, dollars=HITMAN_CONTRACT_BONUS_DOLLARS)
                await _safe_send(
                    bot,
                    hitman_player.user_id,
                    pt(hitman_player).HITMAN_CONTRACT_DONE.format(amount=HITMAN_CONTRACT_BONUS_DOLLARS),
                )

    # 5) Geroy zarbasi (o'lim sababi guruhga aytilmaydi).
    await _resolve_hero_shots(bot, game)

    # 6) Daydi — tashrif buyurgan odami o'ldirilgan bo'lsa, qotilning ismini bilib oladi,
    # agar qotilda yoqilgan Maska bo'lmasa (qurbondagi Maska hech narsa qilmaydi).
    if game.wanderer_target in game.night_kills:
        wanderer_player = next((p for p in _alive(game, Role.WANDERER)), None)
        visited = game.players.get(game.wanderer_target)
        killer_id = game.night_kills[game.wanderer_target]
        culprit = game.players.get(killer_id) if killer_id is not None else None
        if wanderer_player and visited and culprit:
            P = pt(wanderer_player)
            if await use_item(bot, game, culprit, "mask"):
                await _safe_send(bot, wanderer_player.user_id, P.WANDERER_SAW_NOTHING.format(victim=esc(visited.full_name)))
            else:
                add_mvp(game, wanderer_player.user_id, MVP_WANDERER_SAW_KILLER)
                await _safe_send(
                    bot,
                    wanderer_player.user_id,
                    P.WANDERER_SAW_KILLER.format(victim=esc(visited.full_name), killer=esc(culprit.full_name)),
                )

    await _miner_dig(bot, game)
    await _pay_guesses(bot, game)

    for doctor in _alive(game, Role.DOCTOR):
        target_id = game.doctor_targets.get(doctor.user_id)
        if target_id is None:
            game.doctor_last_target.pop(doctor.user_id, None)
        else:
            game.doctor_last_target[doctor.user_id] = target_id
            if target_id == doctor.user_id:
                game.doctor_self_used.add(doctor.user_id)

    if game.night_results:
        await _send_group(bot, game, "\n\n".join(game.night_results))
    elif not game.night_kills:
        await _send_group(bot, game, G.NIGHT_QUIET)
    game.night_results.clear()


def hero_can_shoot(game: Game, player: Player) -> bool:
    return (
        player.alive
        and player.hero_level > 0
        and player.role in HERO_ELIGIBLE_ROLES
        and player.user_id not in game.hero_shot_used
    )


async def _resolve_hero_shots(bot: Bot, game: Game) -> None:
    G = gt(game)
    for shooter_id, target_id in list(game.hero_shots.items()):
        shooter = game.players.get(shooter_id)
        target = game.players.get(target_id)
        if not shooter or shooter_id in game.hero_shot_used or not target:
            continue
        if not target.alive:
            # Nishon shu tunda boshqa sababdan o'lgan — zarba hisobga olinmaydi, keyin yana ishlatish mumkin.
            await _safe_send(bot, shooter.user_id, pt(shooter).HERO_SHOT_KEPT)
            continue
        game.hero_shot_used.add(shooter_id)
        log(game, G.H_HERO.format(actor=_n(shooter), target=_n(target)))

        if shooter.hero_level < HERO_BYPASS_LEVEL:
            if await use_item(bot, game, target, "mirror"):
                # Zarba otgan Geroyning o'ziga qaytadi va to'g'ridan-to'g'ri o'ldiradi.
                await _notify_survived(bot, game, [shooter])
                if shooter.alive:
                    await _kill_player(bot, game, shooter)
                    game.night_kills[shooter.user_id] = target.user_id
                    await _report(bot, game, _death_line(game, G.PREFIX_MAFIA, shooter))
                continue
            if await use_item(bot, game, target, "hero_immunity"):
                await _notify_survived(bot, game, [shooter])
                continue

        await _kill_player(bot, game, target)
        game.night_kills[target.user_id] = shooter.user_id
        await _report(bot, game, _death_line(game, G.PREFIX_MAFIA, target))


def _log_night_choices(game: Game) -> None:
    """Tungi tanlovlar tarixga yoziladi (Komissar, Don, Jurnalist, Josus, Kezuvchi — tanlov paytida handlerda)."""
    p = game.players.get
    G = gt(game)
    for voter_id, target_id in game.mafia_votes.items():
        log(game, G.H_MAFIA_VOTE.format(voter=_n(p(voter_id)), target=_n(p(target_id))))
    for doctor_id, target_id in game.doctor_targets.items():
        log(game, G.H_DOCTOR.format(actor=_n(p(doctor_id)), target=_n(p(target_id))))
    for guard_id, target_id in game.bodyguard_targets.items():
        log(game, G.H_BODYGUARD.format(actor=_n(p(guard_id)), target=_n(p(target_id))))
    single = (
        (Role.KILLER, game.killer_target, G.H_KILLER),
        (Role.HITMAN, game.hitman_target, G.H_HITMAN),
        (Role.WANDERER, game.wanderer_target, G.H_WANDERER),
        (Role.LAWYER, game.advokat_target, G.H_LAWYER),
    )
    for role, target_id, template in single:
        actor = next((pl for pl in _alive(game, role)), None)
        if target_id is not None and actor:
            log(game, template.format(actor=_n(actor), target=_n(p(target_id))))


async def _resolve_cupid(bot: Bot, game: Game) -> None:
    if game.lovers is not None:
        return
    cupid = next((p for p in _alive(game, Role.CUPID)), None)
    if not cupid:
        return
    alive_ids = [p.user_id for p in _alive(game)]
    if len(alive_ids) < 2:
        return
    if len(game.cupid_pick) == 2:
        pair = tuple(game.cupid_pick)
        cupid_text = pt(cupid).CUPID_CHOSEN
    else:
        pair = tuple(random.sample(alive_ids, 2))
        cupid_text = pt(cupid).CUPID_RANDOM
    game.lovers = pair
    first, second = game.players[pair[0]], game.players[pair[1]]
    log(game, gt(game).H_LOVERS.format(first=_n(first), second=_n(second)))
    await _safe_send(bot, cupid.user_id, cupid_text.format(first=esc(first.full_name), second=esc(second.full_name)))
    await _safe_send(bot, first.user_id, pt(first).LOVER_NOTICE.format(partner=esc(second.full_name)))
    await _safe_send(bot, second.user_id, pt(second).LOVER_NOTICE.format(partner=esc(first.full_name)))


async def _miner_dig(bot: Bot, game: Game) -> None:
    """Tirik Konchi har kecha avtomatik qaziydi; topilgan narsa darhol hisobga qo'shiladi."""
    for miner in _alive(game, Role.MINER):
        P = pt(miner)
        roll = random.random()
        if roll < MINER_COIN_CHANCE:
            amount = random.randint(MINER_COIN_MIN, MINER_COIN_MAX)
            await db.add_balance(miner.user_id, coins=amount)
            text = P.MINER_FOUND_COINS.format(amount=amount)
        elif roll < MINER_COIN_CHANCE + MINER_ITEM_CHANCE:
            key = random.choice(MINER_ITEM_POOL)
            await db.add_item(miner.user_id, key, 1)
            text = P.MINER_FOUND_ITEM.format(emoji=ITEMS[key]["emoji"], name=P.ITEM_NAMES[key])
        else:
            text = P.MINER_FOUND_NOTHING
        await _safe_send(bot, miner.user_id, text)


async def _pay_guesses(bot: Bot, game: Game) -> None:
    for guesser_id, target_id in game.guesses.items():
        if target_id in game.night_kills:
            await db.add_balance(guesser_id, coins=GUESS_REWARD_COINS)
            guesser = game.players.get(guesser_id)
            if guesser:
                await _safe_send(bot, guesser_id, pt(guesser).GUESS_WON.format(coins=GUESS_REWARD_COINS))


# ---------- Tong ----------


# ---------- Kun ----------


async def _resolve_sorcerer_revenge(bot: Bot, game: Game, sorcerer) -> None:
    others = [p for p in _alive(game) if p.user_id != sorcerer.user_id]
    if not others:
        return

    await bot.send_message(game.chat_id, gt(game).SORCERER_LAST_WORDS)

    game.revenge_target = None
    game.revenge_event = asyncio.Event()
    kb = build_target_keyboard(game, exclude_ids={sorcerer.user_id}, prefix="sorcerer_revenge")
    await _safe_send(bot, sorcerer.user_id, pt(sorcerer).SORCERER_REVENGE_PROMPT, reply_markup=kb)

    try:
        await asyncio.wait_for(game.revenge_event.wait(), timeout=game.settings.seconds("revenge"))
    except asyncio.TimeoutError:
        pass

    if game.revenge_target is not None:
        target = game.players.get(game.revenge_target)
        if target and target.alive:
            await _kill_player(bot, game, target)
            await _report(bot, game, _death_line(game, gt(game).PREFIX_REVENGE, target))


def confirm_counts(game: Game) -> tuple[int, int]:
    likes = sum(1 for v in game.confirm_votes.values() if v)
    return likes, len(game.confirm_votes) - likes


async def _confirm_vote(bot: Bot, game: Game, candidate: Player) -> bool:
    """Eng ko'p ovoz olgan nomzod uchun guruhda 👍/👎 ovoz o'tkazadi; 👍 ko'p bo'lsa True."""
    game.state = GameState.DAY_CONFIRM
    game.confirm_candidate = candidate.user_id
    game.confirm_votes.clear()
    game.confirm_needed = sum(1 for p in _alive(game) if p.user_id != candidate.user_id)
    game.confirm_event = asyncio.Event()
    confirm_seconds = game.settings.seconds("confirm")

    await bot.send_message(
        game.chat_id,
        gt(game).CONFIRM_PROMPT.format(name=mention(candidate), seconds=_secs(confirm_seconds)),
        reply_markup=build_confirm_keyboard(0, 0),
    )

    try:
        await asyncio.wait_for(game.confirm_event.wait(), timeout=confirm_seconds)
    except asyncio.TimeoutError:
        pass

    likes, dislikes = confirm_counts(game)
    log(game, gt(game).H_CONFIRM.format(name=_n(candidate), likes=likes, dislikes=dislikes))
    game.confirm_candidate = None
    if likes > dislikes:
        return True

    await bot.send_message(
        game.chat_id,
        gt(game).CONFIRM_REJECTED.format(likes=likes, dislikes=dislikes, name=mention(candidate)),
    )
    return False


async def _judge_cancels(bot: Bot, game: Game, candidate: Player) -> bool:
    """Tirik va imkoniyatini ishlatmagan Sudya "judge" sozlamasidagi soniya ichida haydashni bekor qila oladi."""
    judge = next((p for p in _alive(game, Role.JUDGE)), None)
    if not judge or game.judge_used:
        return False

    game.judge_event = asyncio.Event()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=pt(judge).JUDGE_BUTTON, callback_data="judge_cancel")]]
    )
    msg = await _safe_send(
        bot,
        judge.user_id,
        pt(judge).JUDGE_PROMPT.format(name=esc(candidate.full_name), seconds=_secs(game.settings.seconds("judge"))),
        reply_markup=kb,
    )
    try:
        await asyncio.wait_for(game.judge_event.wait(), timeout=game.settings.seconds("judge"))
    except asyncio.TimeoutError:
        pass
    cancelled = game.judge_event.is_set()
    game.judge_event = None

    if msg is not None and not cancelled:
        try:
            await bot.delete_message(judge.user_id, msg.message_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    if cancelled:
        game.judge_used = True
        log(game, gt(game).H_JUDGE)
        await bot.send_message(game.chat_id, gt(game).JUDGE_CANCELLED.format(name=mention(candidate)))
    return cancelled


async def day_phase(bot: Bot, game: Game) -> None:
    game.state = GameState.DAY_DISCUSSION
    G = gt(game)
    log(game, G.HISTORY_DAY.format(n=game.day_number))
    await unlock_chat(bot, game)
    alive = _alive(game)
    discussion = game.settings.discussion_seconds(len(alive))
    voting = game.settings.vote_seconds(len(alive))

    await send_phase_image(
        bot,
        game.chat_id,
        DAY_IMAGE_PATH,
        "day",
        G.DAY_BANNER.format(n=game.day_number),
    )

    username = await _get_bot_username(bot)
    await bot.send_message(
        game.chat_id,
        G.ALIVE_LIST.format(players=_alive_list_text(game)) + "\n\n"
        + G.DISCUSSION_TIME_LEFT.format(seconds=_secs(discussion)),
        reply_markup=_goto_bot_keyboard(game, username),
    )
    await asyncio.sleep(discussion)

    game.state = GameState.DAY_VOTING
    game.day_votes.clear()
    game.vote_needed = len(alive)
    game.vote_event = asyncio.Event()

    await bot.send_message(
        game.chat_id,
        G.VOTING_STARTED.format(seconds=_secs(voting)),
        reply_markup=_goto_bot_keyboard(game, username),
    )

    vote_prompt_tasks = [
        _safe_send_replace(
            bot, game, voter.user_id, pt(voter).VOTE_PROMPT, reply_markup=build_vote_keyboard(game, voter.lang)
        )
        for voter in alive
    ]
    await asyncio.gather(*vote_prompt_tasks)

    async def remind() -> None:
        for voter in _alive(game):
            if voter.user_id not in game.day_votes:
                await _safe_send(bot, voter.user_id, pt(voter).REMINDER_VOTE.format(seconds=REMINDER_BEFORE_END))

    await _wait_with_reminder(game.vote_event, voting, remind)
    # Ovoz berish tugadi: tanlovni o'zgartirish endi mumkin emas.
    game.state = GameState.DAY_CONFIRM
    await flush_announcements(bot, game)

    for voter_id, target_id in game.day_votes.items():
        voter, target = game.players.get(voter_id), game.players.get(target_id) if target_id else None
        log(game, G.H_VOTE.format(voter=_n(voter), target=_n(target)) if target else
            G.H_VOTE_SKIP.format(voter=_n(voter)))

    await _day_phase_result(bot, game)
    await _check_vote_afk(bot, game, alive)


async def _check_vote_afk(bot: Bot, game: Game, voters: list[Player]) -> None:
    """Ovoz bermaganlar hisoblagichi ("ovoz bermaslik" ham ovoz hisoblanadi)."""
    for voter in voters:
        if voter.user_id in game.day_votes:
            voter.missed_votes = 0
            continue
        voter.missed_votes += 1
        if voter.missed_votes >= AFK_LIMIT and voter.alive:
            await kick_afk(bot, game, voter)


async def _day_phase_result(bot: Bot, game: Game) -> None:
    counts = Counter(v for v in game.day_votes.values() if v is not None)
    if counts:
        max_count = max(counts.values())
        candidates = [uid for uid, c in counts.items() if c == max_count]
        if len(candidates) == 1:
            eliminated = game.players[candidates[0]]

            if not await _confirm_vote(bot, game, eliminated):
                return
            if await _judge_cancels(bot, game, eliminated):
                return

            if await use_item(bot, game, eliminated, "vote_shield"):
                await bot.send_message(
                    game.chat_id,
                    gt(game).VOTE_SHIELD_SAVED.format(name=mention(eliminated)),
                )
                return

            if eliminated.role in MAFIA_TEAM_ROLES:
                for voter_id, target_id in game.day_votes.items():
                    if target_id == eliminated.user_id:
                        add_mvp(game, voter_id, MVP_VOTED_OUT_MAFIA)
            await bot.send_message(
                game.chat_id,
                gt(game).ELIMINATED.format(name=mention(eliminated), role=role_reveal(game, eliminated)),
            )
            await _kill_player(bot, game, eliminated)

            if eliminated.role == Role.SORCERER:
                await _resolve_sorcerer_revenge(bot, game, eliminated)
            return

    await bot.send_message(game.chat_id, gt(game).NOBODY_ELIMINATED)


# ---------- O'yin yakuni ----------


async def finish_game(bot: Bot, game: Game, winner: str) -> None:
    game.state = GameState.FINISHED
    await flush_announcements(bot, game)
    await unlock_chat(bot, game)
    result_keys = {"town": "TOWN_WIN_RESULT", "killer": "KILLER_WIN_RESULT", "mafia": "MAFIA_WIN_RESULT"}
    G = gt(game)
    result_text = getattr(G, result_keys[winner])

    private_messages = await payout_game_results(game, winner)
    for user_id, text in private_messages:
        P = pt(game.players[user_id])
        await _safe_send(bot, user_id, f"{P.GAME_OVER}\n\n{getattr(P, result_keys[winner])}\n\n{text}")

    winners = [p for p in game.players.values() if did_win(p, winner)]
    losers = [p for p in game.players.values() if not did_win(p, winner)]

    lines = [G.GAME_OVER, "", result_text, ""]

    idx = 1
    lines.append(G.WINNERS_HEADER)
    for p in winners:
        status = "" if p.alive else G.DEAD_MARK
        lines.append(f"{idx}. {esc(p.full_name)}{hero_badge(p.hero_badge)} — {G.ROLE_NAMES[p.role]}{status}")
        idx += 1

    if losers:
        lines.append("")
        lines.append(G.OTHERS_HEADER)
        for p in losers:
            status = "" if p.alive else G.DEAD_MARK
            lines.append(f"{idx}. {esc(p.full_name)}{hero_badge(p.hero_badge)} — {G.ROLE_NAMES[p.role]}{status}")
            idx += 1

    elapsed_min = max(1, round((time.time() - game.started_at) / 60)) if game.started_at else 0
    lines.append("")
    lines.append(G.GAME_DURATION.format(minutes=elapsed_min))
    lines.append("")
    lines.append(G.RANKING_HINT)

    await _send_group(bot, game, "\n".join(lines))
    if game.history:
        await _send_group(bot, game, "\n".join([G.HISTORY_HEADER, *game.history]))
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
            await unlock_chat(bot, game)
            await bot.send_message(game.chat_id, gt(game).GAME_ERROR)
        except Exception:
            pass
        # remove_game joriy vazifani bekor qiladi — shundan keyin await ishlatib bo'lmaydi.
        manager.remove_game(game.chat_id)
    finally:
        # /stop (boshqa vazifadan bekor qilinganda) guruh yopiq qolib ketmasin.
        if game.announce_task and not game.announce_task.done():
            game.announce_task.cancel()
        if game.chat_locked:
            try:
                await unlock_chat(bot, game)
            except Exception:
                logger.exception("Guruh %s ruxsatlarini tiklashda xatolik", game.chat_id)
