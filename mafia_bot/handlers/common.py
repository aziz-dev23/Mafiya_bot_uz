from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

import db
from texts import HELP_TEXT, WELCOME_PRIVATE

router = Router(name="common")


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start_private(message: Message) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)

    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""

    if payload == "clan":
        from handlers.clan import show_clan_menu

        await show_clan_menu(message)
        return

    await message.answer(WELCOME_PRIVATE)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
