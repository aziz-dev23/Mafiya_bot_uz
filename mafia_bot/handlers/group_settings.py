"""/sozlamalar — guruh adminlari uchun inline tugmali sozlamalar menyusi."""
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Message

import cosmetics
import db
import texts
from economy import GROUP_TITLE_NAME_MAX, OWNER_SHARE_PERCENT
from utils import esc
from i18n import LANG_NAMES
from game.models import Role
from game.roles import SPECIAL_ROLES
from game.settings import (
    LOCK_ALL,
    LOCK_PLAYERS,
    MANDATORY_ROLES,
    MODES,
    PLAYERS_MAX_BOUND,
    PLAYERS_MIN_BOUND,
    TIME_LIMITS,
    GroupSettings,
    load_settings,
    save_settings,
)

router = Router(name="group_settings")

DEFAULT_AUTO_TIME = "20:00"
AUTO_MINUTE_STEP = 15
# Yoqib/o'chiriladigan sozlama -> tugma matni kaliti.
TOGGLES = {
    "items_enabled": "SETTINGS_BTN_ITEMS",
    "hero_enabled": "SETTINGS_BTN_HERO",
    "reveal_roles": "SETTINGS_BTN_REVEAL",
    "last_word": "SETTINGS_BTN_LAST_WORD",
}
# O'chirib-yoqish mumkin bo'lgan rollar (ustuvorlik tartibida, takrorlarsiz).
TOGGLEABLE_ROLES = [r for r in dict.fromkeys(role for role, _ in SPECIAL_ROLES) if r not in MANDATORY_ROLES]


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=f"gs:{data}")


def _flag(value: bool, L=texts) -> str:
    return L.SETTINGS_ON if value else L.SETTINGS_OFF


def main_view(s: GroupSettings, L=texts, share_name: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    rows = [
        [_btn(L.SETTINGS_BTN_TIMES, "times"), _btn(L.SETTINGS_BTN_PLAYERS, "players")],
        [_btn(L.SETTINGS_BTN_ROLES, "roles")],
        *[[_btn(getattr(L, label).format(state=_flag(getattr(s, key), L)), f"tog:{key}")]
          for key, label in TOGGLES.items()],
        [_btn(L.SETTINGS_BTN_VOTES.format(
            state=L.SETTINGS_VOTES_OPEN if s.open_votes else L.SETTINGS_VOTES_ANON), "tog:open_votes")],
        [_btn(L.SETTINGS_BTN_LOCK.format(
            state=L.SETTINGS_LOCK_ALL if s.lock_mode == LOCK_ALL else L.SETTINGS_LOCK_PLAYERS), "lock")],
        [_btn(L.SETTINGS_BTN_MODE.format(state=L.SETTINGS_MODE_NAMES[s.mode]), "mode")],
        [_btn(L.SETTINGS_BTN_AUTO.format(state=s.auto_time or L.SETTINGS_AUTO_OFF), "auto")],
        [InlineKeyboardButton(text=f"🌐 {LANG_NAMES.get(s.lang, s.lang)}", callback_data="lang:groupmenu")],
        [InlineKeyboardButton(
            text=L.SETTINGS_BTN_GROUP_NAME.format(name=s.title_name or L.SETTINGS_GROUP_NAME_DEFAULT),
            callback_data="gsx:name",
        )],
        [InlineKeyboardButton(
            text=L.SETTINGS_BTN_SHARE.format(name=share_name or L.SETTINGS_SHARE_CREATOR), callback_data="gsx:share"
        )],
        [_btn(L.SETTINGS_CLOSE, "close")],
    ]
    return L.SETTINGS_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


def times_view(s: GroupSettings, L=texts) -> tuple[str, InlineKeyboardMarkup]:
    rows = []
    for key, (step, _, _) in TIME_LIMITS.items():
        rows.append([
            _btn(f"−{step}", f"t:{key}:-"),
            _btn(f"{L.SETTINGS_TIME_NAMES[key]}: {getattr(s, key)}", "noop"),
            _btn(f"+{step}", f"t:{key}:+"),
        ])
    rows.append([_btn(L.SETTINGS_BACK, "main")])
    return L.SETTINGS_TIMES_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


def players_view(s: GroupSettings, L=texts) -> tuple[str, InlineKeyboardMarkup]:
    rows = [
        [_btn("−1", "p:min:-"), _btn(L.SETTINGS_MIN_PLAYERS.format(value=s.min_players), "noop"),
         _btn("+1", "p:min:+")],
        [_btn("−1", "p:max:-"), _btn(L.SETTINGS_MAX_PLAYERS.format(value=s.max_players), "noop"),
         _btn("+1", "p:max:+")],
        [_btn(L.SETTINGS_BACK, "main")],
    ]
    return L.SETTINGS_PLAYERS_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


def roles_view(s: GroupSettings, L=texts) -> tuple[str, InlineKeyboardMarkup]:
    disabled = s.disabled_role_set()
    rows = [[_btn(f"{L.ROLE_NAMES[r]} · {L.SETTINGS_ROLE_LOCKED}", "noop")] for r in MANDATORY_ROLES]
    buttons = [_btn(f"{_flag(r not in disabled, L)} {L.ROLE_NAMES[r]}", f"role:{r.value}") for r in TOGGLEABLE_ROLES]
    rows += [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([_btn(L.SETTINGS_BACK, "main")])
    return L.SETTINGS_ROLES_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


def auto_view(s: GroupSettings, L=texts) -> tuple[str, InlineKeyboardMarkup]:
    rows = []
    if s.auto_time:
        rows.append([
            _btn(L.SETTINGS_HOUR_MINUS, "auto:h:-"),
            _btn(L.SETTINGS_AUTO_TIME.format(value=s.auto_time), "noop"),
            _btn(L.SETTINGS_HOUR_PLUS, "auto:h:+"),
        ])
        rows.append([
            _btn(L.SETTINGS_MINUTES_MINUS.format(step=AUTO_MINUTE_STEP), "auto:m:-"),
            _btn(L.SETTINGS_MINUTES_PLUS.format(step=AUTO_MINUTE_STEP), "auto:m:+"),
        ])
        rows.append([_btn(L.SETTINGS_AUTO_TOGGLE_OFF, "auto:toggle")])
    else:
        rows.append([_btn(L.SETTINGS_AUTO_TOGGLE_ON, "auto:toggle")])
    rows.append([_btn(L.SETTINGS_BACK, "main")])
    return L.SETTINGS_AUTO_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


VIEWS = {"main": main_view, "times": times_view, "players": players_view, "roles": roles_view, "auto": auto_view}


def apply_action(s: GroupSettings, action: list[str]) -> str:
    """Sozlamaga o'zgartirish kiritadi va qaysi sahifani ko'rsatish kerakligini qaytaradi."""
    kind = action[0]
    if kind == "t" and action[1] in TIME_LIMITS:
        step, low, high = TIME_LIMITS[action[1]]
        delta = step if action[2] == "+" else -step
        setattr(s, action[1], max(low, min(high, getattr(s, action[1]) + delta)))
        return "times"
    if kind == "p":
        delta = 1 if action[2] == "+" else -1
        if action[1] == "min":
            s.min_players = max(PLAYERS_MIN_BOUND, min(s.max_players, s.min_players + delta))
        else:
            s.max_players = max(s.min_players, min(PLAYERS_MAX_BOUND, s.max_players + delta))
        return "players"
    if kind == "role" and action[1] in Role._value2member_map_:
        role = Role(action[1])
        if role not in MANDATORY_ROLES:
            disabled = set(s.disabled_roles)
            disabled.symmetric_difference_update({role.value})
            s.disabled_roles = sorted(disabled)
        return "roles"
    if kind == "tog" and (action[1] in TOGGLES or action[1] == "open_votes"):
        setattr(s, action[1], not getattr(s, action[1]))
        return "main"
    if kind == "lock":
        s.lock_mode = LOCK_PLAYERS if s.lock_mode == LOCK_ALL else LOCK_ALL
        return "main"
    if kind == "mode":
        s.mode = MODES[(MODES.index(s.mode) + 1) % len(MODES)] if s.mode in MODES else MODES[0]
        return "main"
    if kind == "auto" and len(action) > 1:
        if action[1] == "toggle":
            s.auto_time = None if s.auto_time else DEFAULT_AUTO_TIME
        elif s.auto_time:
            hour, minute = map(int, s.auto_time.split(":"))
            total = hour * 60 + minute
            total += (60 if action[1] == "h" else AUTO_MINUTE_STEP) * (1 if action[2] == "+" else -1)
            total %= 24 * 60
            s.auto_time = f"{total // 60:02d}:{total % 60:02d}"
        return "auto"
    return kind if kind in VIEWS else "main"


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    return member.status in ("administrator", "creator")


async def _share_name(chat_id: int) -> str | None:
    owner_id = await db.get_group_owner_override(chat_id)
    if not owner_id:
        return None
    # Foydalanuvchi yozuvi yaratilmaydi: ulush faqat u botga /start bosgach to'lanadi.
    user = await db.get_user(owner_id)
    return user["full_name"] if user else f"ID {owner_id}"


async def full_main_view(chat_id: int, s: GroupSettings, L=texts) -> tuple[str, InlineKeyboardMarkup]:
    return main_view(s, L, await _share_name(chat_id))


@router.message(Command("sozlamalar", "settings"))
async def cmd_settings(message: Message, bot: Bot, L=texts, UL=texts) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(UL.SETTINGS_GROUP_ONLY)
        return
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.answer(UL.SETTINGS_ADMIN_ONLY)
        return
    text, kb = await full_main_view(message.chat.id, await load_settings(message.chat.id), L)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("gs:"))
async def on_settings(callback: CallbackQuery, bot: Bot, L=texts, UL=texts) -> None:
    chat_id = callback.message.chat.id
    if not await _is_admin(bot, chat_id, callback.from_user.id):
        await callback.answer(UL.SETTINGS_ADMIN_ONLY, show_alert=True)
        return
    action = callback.data.split(":")[1:]
    if action == ["noop"]:
        await callback.answer()
        return
    if action == ["close"]:
        await callback.answer()
        try:
            await callback.message.edit_text(L.SETTINGS_CLOSED)
        except TelegramBadRequest:
            pass
        return

    settings = await load_settings(chat_id)
    view = apply_action(settings, action)
    await save_settings(chat_id, settings)
    if view == "main":
        text, kb = await full_main_view(chat_id, settings, L)
    else:
        text, kb = VIEWS[view](settings, L)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass


# ---------- 🏰 Guruh unvoni nomi va 🤝 ulush oluvchi ----------


class GroupName(StatesGroup):
    waiting = State()


def clean_group_name(raw: str) -> str | None:
    name = " ".join(raw.split())
    return name if 0 < len(name) <= GROUP_TITLE_NAME_MAX else None


@router.callback_query(F.data == "gsx:name")
async def on_group_name(callback: CallbackQuery, bot: Bot, state: FSMContext, L=texts, UL=texts) -> None:
    if not await _is_admin(bot, callback.message.chat.id, callback.from_user.id):
        await callback.answer(UL.SETTINGS_ADMIN_ONLY, show_alert=True)
        return
    await callback.answer()
    await state.set_state(GroupName.waiting)
    await callback.message.answer(
        L.SETTINGS_ASK_GROUP_NAME.format(max=GROUP_TITLE_NAME_MAX), reply_markup=ForceReply(selective=True)
    )


# Faqat botga javob (reply) qilingan xabar — o'yin paytidagi oddiy xabarlar ushlanib qolmasligi uchun.
@router.message(GroupName.waiting, F.text, F.reply_to_message.from_user.is_bot)
async def on_group_name_text(message: Message, bot: Bot, state: FSMContext, L=texts) -> None:
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await state.clear()
        return
    name = clean_group_name(message.text)
    if name is None:
        await message.answer(L.SETTINGS_ASK_GROUP_NAME.format(max=GROUP_TITLE_NAME_MAX),
                             reply_markup=ForceReply(selective=True))
        return
    await state.clear()
    settings = await load_settings(message.chat.id)
    settings.title_name = name
    await save_settings(message.chat.id, settings)
    await cosmetics.load_title(cosmetics.group_title_key(message.chat.id))
    await message.answer(L.SETTINGS_GROUP_NAME_SAVED.format(name=esc(name)))


async def _creator_and_admins(bot: Bot, chat_id: int):
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except TelegramAPIError:
        return None, []
    creator = next((a.user for a in admins if a.status == "creator"), None)
    return creator, [a.user for a in admins if not a.user.is_bot]


@router.callback_query(F.data == "gsx:share")
async def on_share(callback: CallbackQuery, bot: Bot, L=texts, UL=texts) -> None:
    chat_id = callback.message.chat.id
    creator, admins = await _creator_and_admins(bot, chat_id)
    if creator is None or creator.id != callback.from_user.id:
        await callback.answer(UL.SETTINGS_SHARE_CREATOR_ONLY, show_alert=True)
        return
    await callback.answer()
    current = await db.get_group_owner_override(chat_id) or creator.id
    rows = [
        [InlineKeyboardButton(
            text=("✅ " if a.id == current else "") + a.full_name, callback_data=f"gsx:owner:{a.id}"
        )]
        for a in admins
    ]
    rows.append([_btn(L.SETTINGS_BACK, "main")])
    try:
        await callback.message.edit_text(
            L.SETTINGS_SHARE_TITLE.format(percent=OWNER_SHARE_PERCENT), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("gsx:owner:"))
async def on_share_set(callback: CallbackQuery, bot: Bot, L=texts, UL=texts) -> None:
    chat_id = callback.message.chat.id
    raw = callback.data.split(":")[2]
    creator, admins = await _creator_and_admins(bot, chat_id)
    if creator is None or creator.id != callback.from_user.id:
        await callback.answer(UL.SETTINGS_SHARE_CREATOR_ONLY, show_alert=True)
        return
    target = next((a for a in admins if raw.isdigit() and a.id == int(raw)), None)
    if target is None:
        await callback.answer()
        return
    # Yaratuvchining o'zi tanlansa — alohida yozuv kerak emas (standart holat).
    await db.set_group_owner_override(chat_id, None if target.id == creator.id else target.id)
    await callback.answer(UL.SETTINGS_SHARE_SET.format(name=target.full_name), show_alert=True)
    text, kb = await full_main_view(chat_id, await load_settings(chat_id), L)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
