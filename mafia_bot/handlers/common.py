from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

import db
import texts
from game.models import MAFIA_TEAM_ROLES, Role
from texts import HELP_TEXT, ROLE_DESCRIPTIONS, ROLE_NAMES

router = Router(name="common")

JOIN_PREFIX = "join_"


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start_private(message: Message, bot: Bot, command: CommandObject) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)

    args = command.args or ""
    if args.startswith(JOIN_PREFIX) and args[len(JOIN_PREFIX):].lstrip("-").isdigit():
        from handlers.lobby import join_from_deeplink

        await message.answer(await join_from_deeplink(bot, message.from_user, int(args[len(JOIN_PREFIX):])))
        return

    from handlers.menu import MAIN_MENU_TEXT, build_main_menu_keyboard

    me = await bot.get_me()
    await message.answer(MAIN_MENU_TEXT, reply_markup=build_main_menu_keyboard(me.username))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


def build_roles_text() -> list[str]:
    """Barcha rollar tavsifi jamoalar bo'yicha (uzun bo'lgani uchun bir necha xabarga bo'lingan)."""
    solo = (Role.KILLER, Role.SORCERER, Role.WOLF)
    groups = (
        (texts.ROLES_TEAM_MAFIA, [r for r in Role if r in MAFIA_TEAM_ROLES]),
        (texts.ROLES_TEAM_TOWN, [r for r in Role if r not in MAFIA_TEAM_ROLES and r not in solo]),
        (texts.ROLES_TEAM_SOLO, list(solo)),
    )
    messages = []
    for title, roles in groups:
        blocks = [title]
        for role in roles:
            blocks.append(f"<b>{ROLE_NAMES[role]}</b>\n{ROLE_DESCRIPTIONS[role]}")
        messages.append("\n\n".join(blocks))
    messages[0] = texts.ROLES_LIST_HEADER + "\n" + messages[0]
    return messages


@router.message(Command("rollar", "roles"))
async def cmd_roles(message: Message) -> None:
    for text in build_roles_text():
        await message.answer(text)
