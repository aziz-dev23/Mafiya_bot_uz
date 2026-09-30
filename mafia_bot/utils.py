import html

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from game.models import Game
from i18n import get_texts


def esc(text: str) -> str:
    """Foydalanuvchi matnini (ism va h.k.) HTML xabarga xavfsiz qo'yish uchun: `<`, `&` belgilari
    ekranlanmasa Telegram xabarni rad etadi va o'yin to'xtab qolishi mumkin."""
    return html.escape(text, quote=False)


def mention(player) -> str:
    return f'<a href="tg://user?id={player.user_id}">{esc(player.full_name)}</a>'


KEYBOARD_COLUMNS = 2


def _in_columns(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    return [buttons[i : i + KEYBOARD_COLUMNS] for i in range(0, len(buttons), KEYBOARD_COLUMNS)]


def build_target_keyboard(game: Game, exclude_ids: set[int], prefix: str) -> InlineKeyboardMarkup:
    """Faqat tirik o'yinchilar, 2 ustunda."""
    buttons = [
        InlineKeyboardButton(text=p.full_name, callback_data=f"{prefix}:{p.user_id}")
        for p in game.players.values()
        if p.alive and p.user_id not in exclude_ids
    ]
    return InlineKeyboardMarkup(inline_keyboard=_in_columns(buttons))


def build_mafia_kill_keyboard(game: Game, mafia_user_id: int, exclude_ids: set[int]) -> InlineKeyboardMarkup:
    kb = build_target_keyboard(game, exclude_ids, "m_kill")
    mafia = game.players.get(mafia_user_id)
    if mafia and mafia.items.get("rifle", 0) > 0:
        L = get_texts(mafia.lang)
        label = L.RIFLE_ON if mafia_user_id in game.mafia_rifle_users else L.RIFLE_OFF
        kb.inline_keyboard.append([InlineKeyboardButton(text=label, callback_data="m_rifle_toggle")])
    return kb


def build_don_check_keyboard(game: Game, exclude_ids: set[int]) -> InlineKeyboardMarkup:
    return build_target_keyboard(game, exclude_ids, "don_check")


def build_confirm_keyboard(likes: int, dislikes: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"👍 {likes}", callback_data="confirm:yes"),
                InlineKeyboardButton(text=f"👎 {dislikes}", callback_data="confirm:no"),
            ]
        ]
    )


def build_vote_keyboard(game: Game, lang: str | None = None) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=p.full_name, callback_data=f"vote:{p.user_id}")
        for p in game.players.values()
        if p.alive
    ]
    rows = _in_columns(buttons)
    rows.append([InlineKeyboardButton(text=get_texts(lang).VOTE_SKIP_BUTTON, callback_data="vote:skip")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


TELEGRAM_TEXT_LIMIT = 4096


def split_text(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    """Uzun matnni qatorlar bo'yicha limitdan oshmaydigan bo'laklarga ajratadi."""
    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts or [""]
