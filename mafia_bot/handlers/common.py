from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

import db
from texts import HELP_TEXT

router = Router(name="common")


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start_private(message: Message, bot: Bot) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)

    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""

    if payload == "clan":
        from handlers.clan import show_clan_menu

        await show_clan_menu(message)
        return

    from handlers.menu import MAIN_MENU_TEXT, build_main_menu_keyboard

    me = await bot.get_me()
    await message.answer(MAIN_MENU_TEXT, reply_markup=build_main_menu_keyboard(me.username))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
