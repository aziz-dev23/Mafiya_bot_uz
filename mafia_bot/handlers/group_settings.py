"""/sozlamalar — guruh adminlari uchun inline tugmali sozlamalar menyusi."""
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import texts
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
from texts import ROLE_NAMES

router = Router(name="group_settings")

DEFAULT_AUTO_TIME = "20:00"
AUTO_MINUTE_STEP = 15
TOGGLES = {
    "items_enabled": texts.SETTINGS_BTN_ITEMS,
    "hero_enabled": texts.SETTINGS_BTN_HERO,
    "reveal_roles": texts.SETTINGS_BTN_REVEAL,
    "last_word": texts.SETTINGS_BTN_LAST_WORD,
}
# O'chirib-yoqish mumkin bo'lgan rollar (ustuvorlik tartibida, takrorlarsiz).
TOGGLEABLE_ROLES = [r for r in dict.fromkeys(role for role, _ in SPECIAL_ROLES) if r not in MANDATORY_ROLES]


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=f"gs:{data}")


def _flag(value: bool) -> str:
    return texts.SETTINGS_ON if value else texts.SETTINGS_OFF


def main_view(s: GroupSettings) -> tuple[str, InlineKeyboardMarkup]:
    rows = [
        [_btn(texts.SETTINGS_BTN_TIMES, "times"), _btn(texts.SETTINGS_BTN_PLAYERS, "players")],
        [_btn(texts.SETTINGS_BTN_ROLES, "roles")],
        *[[_btn(label.format(state=_flag(getattr(s, key))), f"tog:{key}")] for key, label in TOGGLES.items()],
        [_btn(texts.SETTINGS_BTN_VOTES.format(
            state=texts.SETTINGS_VOTES_OPEN if s.open_votes else texts.SETTINGS_VOTES_ANON), "tog:open_votes")],
        [_btn(texts.SETTINGS_BTN_LOCK.format(
            state=texts.SETTINGS_LOCK_ALL if s.lock_mode == LOCK_ALL else texts.SETTINGS_LOCK_PLAYERS), "lock")],
        [_btn(texts.SETTINGS_BTN_MODE.format(state=texts.SETTINGS_MODE_NAMES[s.mode]), "mode")],
        [_btn(texts.SETTINGS_BTN_AUTO.format(state=s.auto_time or texts.SETTINGS_AUTO_OFF), "auto")],
        [_btn(texts.SETTINGS_CLOSE, "close")],
    ]
    return texts.SETTINGS_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


def times_view(s: GroupSettings) -> tuple[str, InlineKeyboardMarkup]:
    rows = []
    for key, (step, _, _) in TIME_LIMITS.items():
        rows.append([
            _btn(f"−{step}", f"t:{key}:-"),
            _btn(f"{texts.SETTINGS_TIME_NAMES[key]}: {getattr(s, key)}", "noop"),
            _btn(f"+{step}", f"t:{key}:+"),
        ])
    rows.append([_btn(texts.SETTINGS_BACK, "main")])
    return texts.SETTINGS_TIMES_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


def players_view(s: GroupSettings) -> tuple[str, InlineKeyboardMarkup]:
    rows = [
        [_btn("−1", "p:min:-"), _btn(texts.SETTINGS_MIN_PLAYERS.format(value=s.min_players), "noop"),
         _btn("+1", "p:min:+")],
        [_btn("−1", "p:max:-"), _btn(texts.SETTINGS_MAX_PLAYERS.format(value=s.max_players), "noop"),
         _btn("+1", "p:max:+")],
        [_btn(texts.SETTINGS_BACK, "main")],
    ]
    return texts.SETTINGS_PLAYERS_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


def roles_view(s: GroupSettings) -> tuple[str, InlineKeyboardMarkup]:
    disabled = s.disabled_role_set()
    rows = [[_btn(f"{ROLE_NAMES[r]} · {texts.SETTINGS_ROLE_LOCKED}", "noop")] for r in MANDATORY_ROLES]
    buttons = [_btn(f"{_flag(r not in disabled)} {ROLE_NAMES[r]}", f"role:{r.value}") for r in TOGGLEABLE_ROLES]
    rows += [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([_btn(texts.SETTINGS_BACK, "main")])
    return texts.SETTINGS_ROLES_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


def auto_view(s: GroupSettings) -> tuple[str, InlineKeyboardMarkup]:
    rows = []
    if s.auto_time:
        rows.append([
            _btn(texts.SETTINGS_HOUR_MINUS, "auto:h:-"),
            _btn(texts.SETTINGS_AUTO_TIME.format(value=s.auto_time), "noop"),
            _btn(texts.SETTINGS_HOUR_PLUS, "auto:h:+"),
        ])
        rows.append([
            _btn(texts.SETTINGS_MINUTES_MINUS.format(step=AUTO_MINUTE_STEP), "auto:m:-"),
            _btn(texts.SETTINGS_MINUTES_PLUS.format(step=AUTO_MINUTE_STEP), "auto:m:+"),
        ])
        rows.append([_btn(texts.SETTINGS_AUTO_TOGGLE_OFF, "auto:toggle")])
    else:
        rows.append([_btn(texts.SETTINGS_AUTO_TOGGLE_ON, "auto:toggle")])
    rows.append([_btn(texts.SETTINGS_BACK, "main")])
    return texts.SETTINGS_AUTO_TITLE, InlineKeyboardMarkup(inline_keyboard=rows)


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


@router.message(Command("sozlamalar", "settings"))
async def cmd_settings(message: Message, bot: Bot) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(texts.SETTINGS_GROUP_ONLY)
        return
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.answer(texts.SETTINGS_ADMIN_ONLY)
        return
    text, kb = main_view(await load_settings(message.chat.id))
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("gs:"))
async def on_settings(callback: CallbackQuery, bot: Bot) -> None:
    chat_id = callback.message.chat.id
    if not await _is_admin(bot, chat_id, callback.from_user.id):
        await callback.answer(texts.SETTINGS_ADMIN_ONLY, show_alert=True)
        return
    action = callback.data.split(":")[1:]
    if action == ["noop"]:
        await callback.answer()
        return
    if action == ["close"]:
        await callback.answer()
        try:
            await callback.message.edit_text(texts.SETTINGS_CLOSED)
        except TelegramBadRequest:
            pass
        return

    settings = await load_settings(chat_id)
    view = apply_action(settings, action)
    await save_settings(chat_id, settings)
    text, kb = VIEWS[view](settings)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
