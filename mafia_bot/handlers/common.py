from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import purchases
import texts
from game.models import MAFIA_TEAM_ROLES, Role
from game.settings import load_settings, save_settings
from i18n import LANG_NAMES, LANGS, RU, UZ, get_texts, set_user_lang

router = Router(name="common")

JOIN_PREFIX = "join_"
REF_PREFIX = "ref_"


def _lang_from_telegram(language_code: str | None) -> str:
    """Yangi foydalanuvchi uchun boshlang'ich til: Telegram ilovasi ruscha bo'lsa — rus, aks holda o'zbek."""
    return RU if (language_code or "").startswith(("ru", "be", "kk")) else UZ


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start_private(message: Message, bot: Bot, command: CommandObject, L=texts) -> None:
    user = message.from_user
    is_new = await db.get_user(user.id) is None
    await db.ensure_user(user.id, user.full_name, user.username)
    if is_new:
        lang = _lang_from_telegram(user.language_code)
        await set_user_lang(user.id, lang)
        L = get_texts(lang)

    args = command.args or ""
    if is_new and args.startswith(REF_PREFIX) and args[len(REF_PREFIX):].isdigit():
        # 🔗 Faqat yangi foydalanuvchi; o'zini o'zi taklif qila olmaydi, taklif qilgan botda bo'lishi kerak.
        referrer_id = int(args[len(REF_PREFIX):])
        if referrer_id != user.id and await db.get_user(referrer_id) is not None:
            await db.add_referral(user.id, referrer_id)
    # 🤝 /start bosmagan guruh egasiga yig'ilgan ulush endi to'lanadi.
    await purchases.settle_and_notify(bot, user.id)
    if args.startswith(JOIN_PREFIX) and args[len(JOIN_PREFIX):].lstrip("-").isdigit():
        from handlers.lobby import join_from_deeplink

        await message.answer(await join_from_deeplink(bot, user, int(args[len(JOIN_PREFIX):]), L))
        return

    from handlers.menu import build_main_menu_keyboard, main_menu_text

    me = await bot.get_me()
    await message.answer(main_menu_text(L), reply_markup=build_main_menu_keyboard(me.username, L))


@router.message(Command("help"))
async def cmd_help(message: Message, L=texts) -> None:
    await message.answer(L.HELP_TEXT)


def build_roles_text(L=texts) -> list[str]:
    """Barcha rollar tavsifi jamoalar bo'yicha (uzun bo'lgani uchun bir necha xabarga bo'lingan)."""
    solo = (Role.KILLER, Role.SORCERER, Role.WOLF)
    groups = (
        (L.ROLES_TEAM_MAFIA, [r for r in Role if r in MAFIA_TEAM_ROLES]),
        (L.ROLES_TEAM_TOWN, [r for r in Role if r not in MAFIA_TEAM_ROLES and r not in solo]),
        (L.ROLES_TEAM_SOLO, list(solo)),
    )
    messages = []
    for title, roles in groups:
        blocks = [title]
        for role in roles:
            blocks.append(f"<b>{L.ROLE_NAMES[role]}</b>\n{L.ROLE_DESCRIPTIONS[role]}")
        messages.append("\n\n".join(blocks))
    messages[0] = L.ROLES_LIST_HEADER + "\n" + messages[0]
    return messages


@router.message(Command("rollar", "roles"))
async def cmd_roles(message: Message, L=texts) -> None:
    for text in build_roles_text(L):
        await message.answer(text)


# ---------- Til tanlash (/til) ----------


def language_keyboard(scope: str) -> InlineKeyboardMarkup:
    """scope: "user" — foydalanuvchi tili, "group" — guruh tili."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=LANG_NAMES[code], callback_data=f"lang:{scope}:{code}")]
                         for code in LANGS]
    )


async def _is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    return member.status in ("administrator", "creator")


@router.message(Command("til", "lang", "language", "yazyk"))
async def cmd_language(message: Message, bot: Bot, L=texts, UL=texts) -> None:
    if message.chat.type in ("group", "supergroup"):
        if not await _is_group_admin(bot, message.chat.id, message.from_user.id):
            await message.answer(UL.LANG_ADMIN_ONLY)
            return
        await message.answer(L.LANG_GROUP_PROMPT, reply_markup=language_keyboard("group"))
        return
    await message.answer(UL.LANG_PROMPT, reply_markup=language_keyboard("user"))


@router.callback_query(F.data == "lang:menu")
async def on_language_menu(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    await callback.message.answer(UL.LANG_PROMPT, reply_markup=language_keyboard("user"))


@router.callback_query(F.data == "lang:groupmenu")
async def on_group_language_menu(callback: CallbackQuery, bot: Bot, L=texts, UL=texts) -> None:
    if not await _is_group_admin(bot, callback.message.chat.id, callback.from_user.id):
        await callback.answer(UL.LANG_ADMIN_ONLY, show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(L.LANG_GROUP_PROMPT, reply_markup=language_keyboard("group"))


@router.callback_query(F.data.startswith("lang:user:"))
async def on_set_user_language(callback: CallbackQuery) -> None:
    code = callback.data.rsplit(":", 1)[1]
    if code not in LANGS:
        await callback.answer()
        return
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    await set_user_lang(callback.from_user.id, code)
    L = get_texts(code)
    done = L.LANG_SET.format(name=LANG_NAMES[code])
    await callback.answer(done)
    try:
        await callback.message.edit_text(done)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("lang:group:"))
async def on_set_group_language(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    code = callback.data.rsplit(":", 1)[1]
    chat_id = callback.message.chat.id
    if code not in LANGS:
        await callback.answer()
        return
    if not await _is_group_admin(bot, chat_id, callback.from_user.id):
        await callback.answer(UL.LANG_ADMIN_ONLY, show_alert=True)
        return
    settings = await load_settings(chat_id)
    settings.lang = code
    await save_settings(chat_id, settings)
    L = get_texts(code)
    await callback.answer()
    try:
        await callback.message.edit_text(L.LANG_GROUP_SET.format(name=LANG_NAMES[code]))
    except TelegramBadRequest:
        pass
