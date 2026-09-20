import asyncio

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, User

import db
from config import LOBBY_AUTOSTART_DELAY, MAX_PLAYERS, MIN_PLAYERS
from game.engine import run_game
from game.manager import manager
from game.models import Game, GameState, Player, Role
from game.roles import assign_roles
from texts import ROLE_DESCRIPTIONS, ROLE_NAMES
from utils import mention

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
        f"Jami {len(game.players)}ta odam.",
    ]
    return "\n".join(lines)


def build_lobby_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🤵‍♂️🤵‍♀️ Qo'shilish", callback_data="lobby:join")]]
    )


def build_role_message(player: Player, game: Game) -> str:
    lines = [f"🎭 Sizning rolingiz: <b>{ROLE_NAMES[player.role]}</b>", "", ROLE_DESCRIPTIONS[player.role]]
    if player.role in (Role.MAFIA, Role.DON, Role.LAWYER):
        teammates = [
            p.full_name
            for p in game.players.values()
            if p.role in (Role.MAFIA, Role.DON, Role.LAWYER) and p.user_id != player.user_id
        ]
        if teammates:
            lines.append("")
            lines.append("Sherik mafiyalar: " + ", ".join(teammates))
    if player.role == Role.HITMAN and player.contract_target is not None:
        target = game.players.get(player.contract_target)
        if target:
            lines.append("")
            lines.append(f"🎯 Sizning maxfiy buyurtma nishoningiz: <b>{target.full_name}</b>")
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

    game = manager.create_game(message.chat.id, message.from_user.id)
    ok = await try_register_player(bot, game, message.from_user)
    if not ok:
        manager.remove_game(message.chat.id)
        me = await bot.get_me()
        await message.answer(
            "Avval botga shaxsiy xabar yozib, /start bosing, so'ng qayta urinib ko'ring: "
            f"https://t.me/{me.username}"
        )
        return

    msg = await message.answer(build_lobby_text(game), reply_markup=build_lobby_keyboard())
    game.lobby_message_id = msg.message_id


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
    if len(game.players) >= MAX_PLAYERS:
        await callback.answer("Ro'yxat to'lgan.", show_alert=True)
        return
    other_game = manager.get_game_by_player(callback.from_user.id)
    if other_game:
        await callback.answer("Siz boshqa o'yinda ishtirok etyapsiz.", show_alert=True)
        return

    ok = await try_register_player(bot, game, callback.from_user)
    if not ok:
        me = await bot.get_me()
        await callback.answer(
            f"Avval botga shaxsiy yozib /start bosing (@{me.username}), keyin qayta urinib ko'ring.",
            show_alert=True,
        )
        return

    await callback.answer("Qo'shildingiz! ✅")
    try:
        await callback.message.edit_text(build_lobby_text(game), reply_markup=build_lobby_keyboard())
    except TelegramBadRequest:
        pass

    if game.state != GameState.LOBBY or game.starting:
        return

    if len(game.players) >= MAX_PLAYERS:
        game.starting = True
        await _start_game(bot, game)
    elif len(game.players) >= MIN_PLAYERS and not game.autostart_scheduled:
        game.autostart_scheduled = True
        asyncio.create_task(_autostart_countdown(bot, game))


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

    async def _load_items(player: Player) -> None:
        player.items = await db.get_enabled_items(player.user_id)

    await asyncio.gather(*(_load_items(p) for p in game.players.values()))

    try:
        await bot.edit_message_text(
            "🎮 O'yin boshlandi! Rollar shaxsiy xabarlarga yuborildi.",
            chat_id=game.chat_id,
            message_id=game.lobby_message_id,
        )
    except TelegramBadRequest:
        pass

    group_kb = await _group_return_keyboard(bot, game.chat_id)

    async def _send_role(player: Player) -> None:
        try:
            await bot.send_message(player.user_id, build_role_message(player, game), reply_markup=group_kb)
        except (TelegramForbiddenError, TelegramBadRequest):
            pass

    await asyncio.gather(*(_send_role(p) for p in game.players.values()))

    asyncio.create_task(run_game(bot, game))


async def _autostart_countdown(bot: Bot, game: Game) -> None:
    try:
        await bot.send_message(
            game.chat_id,
            f"✅ Kamida {MIN_PLAYERS} o'yinchi yig'ildi! {LOBBY_AUTOSTART_DELAY} soniyadan so'ng o'yin "
            "avtomatik boshlanadi (hali ham qo'shilishingiz mumkin).",
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass

    await asyncio.sleep(LOBBY_AUTOSTART_DELAY)

    if manager.get_game(game.chat_id) is not game or game.state != GameState.LOBBY or game.starting:
        return
    game.starting = True
    await _start_game(bot, game)
