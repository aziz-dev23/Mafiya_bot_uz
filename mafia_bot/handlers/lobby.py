import asyncio

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, User

import db
from config import MAX_PLAYERS, MIN_PLAYERS
from game.engine import run_game
from game.manager import manager
from game.models import Game, GameState, Player
from game.roles import assign_roles
from texts import ROLE_DESCRIPTIONS, ROLE_NAMES

router = Router(name="lobby")


def build_lobby_text(game: Game) -> str:
    lines = [
        "🎲 <b>Yangi Mafiya o'yini!</b>",
        f"👥 Qatnashuvchilar: {len(game.players)}/{MAX_PLAYERS} (kamida {MIN_PLAYERS} kerak)",
        "",
    ]
    for i, p in enumerate(game.players.values(), 1):
        lines.append(f"{i}. {p.full_name}")
    lines.append("")
    lines.append("Qo'shilish uchun pastdagi tugmani bosing 👇")
    return "\n".join(lines)


def build_lobby_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Qo'shilish", callback_data="lobby:join")],
            [
                InlineKeyboardButton(text="▶️ Boshlash", callback_data="lobby:start"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="lobby:cancel"),
            ],
        ]
    )


def build_role_message(player: Player, game: Game) -> str:
    lines = [f"🎭 Sizning rolingiz: <b>{ROLE_NAMES[player.role]}</b>", "", ROLE_DESCRIPTIONS[player.role]]
    if player.role.value == "mafia":
        teammates = [p.full_name for p in game.players.values() if p.role == player.role and p.user_id != player.user_id]
        if teammates:
            lines.append("")
            lines.append("Sherik mafiyalar: " + ", ".join(teammates))
    return "\n".join(lines)


async def try_register_player(bot: Bot, game: Game, user: User) -> bool:
    if user.id in game.players:
        return True
    try:
        await bot.send_message(
            user.id,
            "✅ Siz Mafiya o'yiniga qo'shildingiz! O'yin boshlanganda rolingiz shu yerga yuboriladi.",
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        return False

    await db.ensure_user(user.id, user.full_name, user.username)
    clan_row = await db.get_user_clan(user.id)
    clan_tag = clan_row["tag"] if clan_row else None

    game.players[user.id] = Player(
        user_id=user.id, full_name=user.full_name, username=user.username, clan_tag=clan_tag
    )
    manager.register_player(game, user.id)
    return True


@router.message(Command("mafia", "yangi_oyin"))
async def cmd_new_game(message: Message, bot: Bot) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Bu buyruq faqat guruhda ishlaydi. Botni guruhga qo'shing va shu yerda ishga tushiring.")
        return

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


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    game = manager.get_game(message.chat.id)
    if not game:
        await message.answer("Bu guruhda faol o'yin yo'q.")
        return
    if message.from_user.id != game.host_id:
        await message.answer("Faqat o'yinni boshlagan odam uni to'xtata oladi.")
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


@router.callback_query(F.data == "lobby:start")
async def on_start(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game(callback.message.chat.id)
    if not game or game.state != GameState.LOBBY:
        await callback.answer("Ro'yxat topilmadi.", show_alert=True)
        return
    if callback.from_user.id != game.host_id:
        await callback.answer("Faqat o'yinni boshlagan odam uni ishga tushira oladi.", show_alert=True)
        return
    if len(game.players) < MIN_PLAYERS:
        await callback.answer(f"Kamida {MIN_PLAYERS} o'yinchi kerak.", show_alert=True)
        return

    await callback.answer("O'yin boshlanmoqda...")
    assign_roles(game)

    try:
        await callback.message.edit_text("🎮 O'yin boshlandi! Rollar shaxsiy xabarlarga yuborildi.")
    except TelegramBadRequest:
        pass

    for p in game.players.values():
        try:
            await bot.send_message(p.user_id, build_role_message(p, game))
        except (TelegramForbiddenError, TelegramBadRequest):
            pass

    asyncio.create_task(run_game(bot, game))


@router.callback_query(F.data == "lobby:cancel")
async def on_cancel(callback: CallbackQuery) -> None:
    game = manager.get_game(callback.message.chat.id)
    if not game:
        await callback.answer("O'yin topilmadi.")
        return
    if callback.from_user.id != game.host_id:
        await callback.answer("Faqat o'yinni boshlagan odam bekor qila oladi.", show_alert=True)
        return

    manager.remove_game(game.chat_id)
    await callback.answer("Bekor qilindi.")
    try:
        await callback.message.edit_text("❌ O'yin bekor qilindi.")
    except TelegramBadRequest:
        pass
