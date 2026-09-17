from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from game.models import Game


def mention(player) -> str:
    return f'<a href="tg://user?id={player.user_id}">{player.full_name}</a>'


def build_target_keyboard(game: Game, exclude_ids: set[int], prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=p.full_name, callback_data=f"{prefix}:{p.user_id}")]
        for p in game.players.values()
        if p.alive and p.user_id not in exclude_ids
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_mafia_kill_keyboard(game: Game, mafia_user_id: int, exclude_ids: set[int]) -> InlineKeyboardMarkup:
    kb = build_target_keyboard(game, exclude_ids, "m_kill")
    mafia = game.players.get(mafia_user_id)
    if mafia and mafia.items.get("rifle", 0) > 0:
        rifle_on = mafia_user_id in game.mafia_rifle_users
        label = "🔫 Miltiq bilan otish: YONIQ ✅" if rifle_on else "🔫 Miltiq bilan otish: O'CHIQ"
        kb.inline_keyboard.append([InlineKeyboardButton(text=label, callback_data="m_rifle_toggle")])
    return kb


def build_don_check_keyboard(game: Game, exclude_ids: set[int]) -> InlineKeyboardMarkup:
    return build_target_keyboard(game, exclude_ids, "don_check")


def build_vote_keyboard(game: Game) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=p.full_name, callback_data=f"vote:{p.user_id}")]
        for p in game.players.values()
        if p.alive
    ]
    buttons.append([InlineKeyboardButton(text="🚫 Ovoz bermaslik", callback_data="vote:skip")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


