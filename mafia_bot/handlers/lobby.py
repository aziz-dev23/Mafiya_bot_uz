import asyncio
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, User

import db
import texts
from config import LOBBY_EDIT_INTERVAL, NEWBIE_GAMES
from economy import ITEM_MAX_USES_PER_GAME, MAFIA_TEAM_ROLES
from game.engine import run_game
from game.manager import manager
from game.models import Game, GameState, Player, Role
from game.roles import assign_roles
from game.settings import load_settings
from texts import ROLE_DESCRIPTIONS, ROLE_NAMES
from utils import esc, mention

router = Router(name="lobby")


def build_lobby_text(game: Game) -> str:
    names = ", ".join(mention(p) for p in game.players.values()) or "—"
    lines = [
        "🎭 <b>Mafiya Gamer's</b>",
        "",
        "<b>Ro'yxatdan o'tish boshlandi</b>",
        "",
        "Ro'yxatdan o'tganlar:",
        names,
        "",
        f"Jami {len(game.players)}ta odam. (kamida {game.settings.min_players} kerak)",
        "",
        "▶️ Boshlash tugmasini faqat o'yin egasi yoki guruh adminlari bosa oladi.",
    ]
    return "\n".join(lines)


def build_lobby_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🤵‍♂️🤵‍♀️ Qo'shilish", callback_data="lobby:join"),
                InlineKeyboardButton(text=texts.LOBBY_LEAVE_BUTTON, callback_data="lobby:leave"),
            ],
            [InlineKeyboardButton(text="▶️ Boshlash", callback_data="lobby:start_now")],
        ]
    )


def build_role_message(player: Player, game: Game) -> str:
    lines = [f"🎭 Sizning rolingiz: <b>{ROLE_NAMES[player.role]}</b>", "", ROLE_DESCRIPTIONS[player.role]]
    if player.role in MAFIA_TEAM_ROLES:
        teammates = [
            esc(p.full_name)
            for p in game.players.values()
            if p.role in MAFIA_TEAM_ROLES and p.user_id != player.user_id
        ]
        if teammates:
            lines.append("")
            lines.append("Sherik mafiyalar: " + ", ".join(teammates))
    if player.role == Role.SERGEANT:
        detective = next((p for p in game.players.values() if p.role == Role.DETECTIVE), None)
        if detective:
            lines.append("")
            lines.append(texts.SERGEANT_KNOWS.format(name=esc(detective.full_name)))
    if player.role == Role.HITMAN and player.contract_target is not None:
        target = game.players.get(player.contract_target)
        if target:
            lines.append("")
            lines.append(f"🎯 Sizning maxfiy buyurtma nishoningiz: <b>{esc(target.full_name)}</b>")
    if player.role in texts.ROLE_TIPS:
        lines.append("")
        lines.append(texts.ROLE_TIP_PREFIX + texts.ROLE_TIPS[player.role])
    if player.games_played < NEWBIE_GAMES:
        lines.append("")
        lines.append(texts.NEWBIE_TIPS)
    return "\n".join(lines)


async def try_register_player(bot: Bot, game: Game, user: User) -> bool:
    if user.id in game.players:
        return True
    try:
        # Shaxsiy xabar yuborish shart — shu orqali bot ushbu foydalanuvchiga yoza olishini
        # tekshiramiz. Lekin "qo'shildingiz" degan alohida xabarni chatda qoldirmaymiz —
        # o'yinchi faqat o'yin boshlanganda o'z rolini ko'rishi kerak.
        probe = await bot.send_message(
            user.id,
            "✅ Siz Mafiya o'yiniga qo'shildingiz! O'yin boshlanganda rolingiz shu yerga yuboriladi.",
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        return False

    try:
        await bot.delete_message(user.id, probe.message_id)
    except TelegramBadRequest:
        pass

    await db.ensure_user(user.id, user.full_name, user.username)

    game.players[user.id] = Player(user_id=user.id, full_name=user.full_name, username=user.username)
    manager.register_player(game, user.id)
    return True


async def _open_new_game(message: Message, bot: Bot) -> None:
    if manager.get_game(message.chat.id):
        await message.answer("Bu guruhda allaqachon o'yin ketyapti yoki ro'yxat ochiq.")
        return

    if manager.get_game_by_player(message.from_user.id):
        await message.answer("Siz allaqachon boshqa o'yinda ishtirok etyapsiz.")
        return

    await open_lobby(bot, message.chat.id, message.from_user)


async def open_lobby(bot: Bot, chat_id: int, host: User | None = None) -> Game | None:
    """Guruhda yangi ro'yxat ochadi. host=None — avtomatik o'yin (faqat adminlar boshlay oladi)."""
    game = manager.create_game(chat_id, host.id if host else 0)
    game.settings = await load_settings(chat_id)
    if host is not None and not await try_register_player(bot, game, host):
        manager.remove_game(chat_id)
        me = await bot.get_me()
        await bot.send_message(
            chat_id,
            "Avval botga shaxsiy xabar yozib, /start bosing, so'ng qayta urinib ko'ring: "
            f"https://t.me/{me.username}",
        )
        return None

    msg = await bot.send_message(chat_id, build_lobby_text(game), reply_markup=build_lobby_keyboard())
    game.lobby_message_id = msg.message_id
    game.lobby_last_edit = time.monotonic()
    try:
        # Ro'yxat xabari hamma ko'rishi uchun guruh tepasiga qadaladi (bot admin bo'lishi kerak).
        await bot.pin_chat_message(chat_id, msg.message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
    return game


async def _unpin_lobby(bot: Bot, game: Game) -> None:
    if game.lobby_message_id is None:
        return
    try:
        await bot.unpin_chat_message(game.chat_id, message_id=game.lobby_message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


@router.message(Command("mafia", "yangi_oyin"))
async def cmd_new_game(message: Message, bot: Bot) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Bu buyruq faqat guruhda ishlaydi. Botni guruhga qo'shing va shu yerda ishga tushiring.")
        return
    await _open_new_game(message, bot)


@router.message(CommandStart(), F.chat.type.in_({"group", "supergroup"}))
async def cmd_start_group(message: Message, bot: Bot) -> None:
    game = manager.get_game(message.chat.id)
    if not game:
        await _open_new_game(message, bot)
        return

    if game.state != GameState.LOBBY:
        await message.answer("Bu guruhda o'yin allaqachon boshlangan. U tugagach /start bosib yangisini oching.")
        return

    if message.from_user.id in game.players:
        await message.answer("Siz allaqachon ro'yxatdasiz. O'yin tez orada boshlanadi!")
        return

    await message.answer(
        "🎮 Bu guruhda o'yin ro'yxati ochiq! Qo'shilish uchun tugmani bosing:",
        reply_markup=build_lobby_keyboard(),
    )


async def _is_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    return member.status in ("administrator", "creator")


@router.message(Command("stop"))
async def cmd_stop(message: Message, bot: Bot) -> None:
    game = manager.get_game(message.chat.id)
    if not game:
        await message.answer("Bu guruhda faol o'yin yo'q.")
        return
    if not await _is_chat_admin(bot, message.chat.id, message.from_user.id):
        await message.answer("Faqat guruh adminlari o'yinni to'xtata oladi.")
        return
    manager.remove_game(message.chat.id)
    if game.state == GameState.LOBBY:
        await _unpin_lobby(bot, game)
    await message.answer("🛑 O'yin to'xtatildi.")


@router.callback_query(F.data == "lobby:join")
async def on_join(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game(callback.message.chat.id)
    if not game or game.state != GameState.LOBBY:
        await callback.answer("Ro'yxat yopiq.", show_alert=True)
        return
    if callback.from_user.id in game.players:
        await callback.answer("Siz allaqachon qo'shilgansiz.")
        return
    if len(game.players) >= game.settings.max_players:
        await callback.answer("Ro'yxat to'lgan.", show_alert=True)
        return
    other_game = manager.get_game_by_player(callback.from_user.id)
    if other_game:
        await callback.answer("Siz boshqa o'yinda ishtirok etyapsiz.", show_alert=True)
        return

    ok = await try_register_player(bot, game, callback.from_user)
    if not ok:
        # Bot bu odamga yoza olmaydi (hali /start bosmagan): botni ochib beramiz — /start bosilishi
        # bilan u shu guruh ro'yxatiga avtomatik qo'shiladi (handlers/common.py).
        me = await bot.get_me()
        await callback.answer(url=f"https://t.me/{me.username}?start=join_{game.chat_id}")
        return

    await callback.answer("Qo'shildingiz! ✅")
    schedule_lobby_edit(bot, game)


@router.callback_query(F.data == "lobby:leave")
async def on_leave(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game(callback.message.chat.id)
    if not game or game.state != GameState.LOBBY or game.starting:
        await callback.answer("Ro'yxat yopiq.", show_alert=True)
        return
    if callback.from_user.id not in game.players:
        await callback.answer(texts.LOBBY_NOT_IN)
        return
    del game.players[callback.from_user.id]
    manager.unregister_player(game, callback.from_user.id)
    await callback.answer(texts.LOBBY_LEFT)
    schedule_lobby_edit(bot, game)


async def join_from_deeplink(bot: Bot, user: User, chat_id: int) -> str:
    """/start join_<chat_id> — "Qo'shilish"ni bosgan, lekin botga hali yozmagan odam shu yerga keladi."""
    game = manager.get_game(chat_id)
    if not game or game.state != GameState.LOBBY or game.starting:
        return texts.JOIN_VIA_START_CLOSED
    if user.id in game.players:
        return texts.JOIN_VIA_START_OK
    other = manager.get_game_by_player(user.id)
    if other is not None:
        return texts.JOIN_VIA_START_OTHER_GAME
    if len(game.players) >= game.settings.max_players:
        return texts.JOIN_VIA_START_FULL
    if not await try_register_player(bot, game, user):
        return texts.JOIN_VIA_START_CLOSED
    schedule_lobby_edit(bot, game)
    return texts.JOIN_VIA_START_OK


def schedule_lobby_edit(bot: Bot, game: Game) -> None:
    """Ro'yxat xabarini ko'pi bilan LOBBY_EDIT_INTERVAL soniyada bir marta tahrirlaydi:
    shu oraliqdagi barcha qo'shilishlar bitta tahrirda aks etadi."""
    if game.lobby_edit_task is None or game.lobby_edit_task.done():
        game.lobby_edit_task = asyncio.create_task(_edit_lobby_later(bot, game))


async def _edit_lobby_later(bot: Bot, game: Game) -> None:
    await asyncio.sleep(max(0.0, game.lobby_last_edit + LOBBY_EDIT_INTERVAL - time.monotonic()))
    if game.state != GameState.LOBBY or game.starting or manager.get_game(game.chat_id) is not game:
        return
    game.lobby_last_edit = time.monotonic()
    try:
        await bot.edit_message_text(
            build_lobby_text(game),
            chat_id=game.chat_id,
            message_id=game.lobby_message_id,
            reply_markup=build_lobby_keyboard(),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "lobby:start_now")
async def on_start_now(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game(callback.message.chat.id)
    if not game or game.state != GameState.LOBBY:
        await callback.answer("Ro'yxat yopiq.", show_alert=True)
        return
    if game.starting:
        await callback.answer("O'yin allaqachon boshlanmoqda.", show_alert=True)
        return

    is_owner = callback.from_user.id == game.host_id
    if not is_owner and not await _is_chat_admin(bot, game.chat_id, callback.from_user.id):
        await callback.answer("Faqat o'yin egasi yoki guruh adminlari boshlashi mumkin.", show_alert=True)
        return

    if len(game.players) < game.settings.min_players:
        await callback.answer(f"Kamida {game.settings.min_players} o'yinchi kerak.", show_alert=True)
        return

    game.starting = True
    await callback.answer("O'yin boshlanmoqda... ▶️")
    await _start_game(bot, game)


async def _group_return_keyboard(bot: Bot, chat_id: int) -> InlineKeyboardMarkup | None:
    """Guruhga qaytish tugmasi uchun havola topadi (ochiq guruh username'i yoki taklif havolasi)."""
    url = None
    try:
        chat = await bot.get_chat(chat_id)
        if chat.username:
            url = f"https://t.me/{chat.username}"
        else:
            url = chat.invite_link
    except (TelegramBadRequest, TelegramForbiddenError):
        pass

    if not url:
        try:
            url = await bot.export_chat_invite_link(chat_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            return None

    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Guruhga qaytish", url=url)]])


async def _start_game(bot: Bot, game: Game) -> None:
    assign_roles(game)

    async def _load_player_data(player: Player) -> None:
        # Har bir buyum turidan bir o'yinda ko'pi bilan ITEM_MAX_USES_PER_GAME dona ishlaydi.
        # Guruh sozlamasida buyumlar yoki Geroy o'chirilgan bo'lsa, ular bu o'yinda ishlamaydi.
        if game.settings.items_active:
            enabled = await db.get_enabled_items(player.user_id)
            player.items = {key: min(count, ITEM_MAX_USES_PER_GAME) for key, count in enabled.items()}
        if game.settings.hero_active:
            player.hero_level = await db.get_hero_level(player.user_id)
        row = await db.get_user(player.user_id)
        player.games_played = row["games"] if row else 0

    await asyncio.gather(*(_load_player_data(p) for p in game.players.values()))

    try:
        await bot.edit_message_text(
            "🎮 O'yin boshlandi! Rollar shaxsiy xabarlarga yuborildi.",
            chat_id=game.chat_id,
            message_id=game.lobby_message_id,
        )
    except TelegramBadRequest:
        pass

    await _unpin_lobby(bot, game)
    group_kb = await _group_return_keyboard(bot, game.chat_id)

    async def _send_role(player: Player) -> None:
        try:
            await bot.send_message(player.user_id, build_role_message(player, game), reply_markup=group_kb)
        except (TelegramForbiddenError, TelegramBadRequest):
            pass

    await asyncio.gather(*(_send_role(p) for p in game.players.values()))

    asyncio.create_task(run_game(bot, game))
