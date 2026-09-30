"""Halok bo'lgan o'yinchilarning botga yozgan xabarlari: avval so'nggi so'z (guruhga chiqadi),
keyin o'liklar chati (boshqa halok bo'lganlarga yetkaziladi)."""
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Filter
from aiogram.types import Message

import texts
from config import LAST_WORD_MAX_LENGTH
from game.manager import manager
from game.models import Game, GameState, Player
from i18n import get_texts
from utils import esc, mention

router = Router(name="afterlife")


class DeadPlayerFilter(Filter):
    async def __call__(self, message: Message) -> bool | dict:
        if not message.from_user or not message.text or message.text.startswith("/"):
            return False
        game = manager.get_game_by_player(message.from_user.id)
        if not game or game.state in (GameState.LOBBY, GameState.FINISHED):
            return False
        player = game.players.get(message.from_user.id)
        if not player or player.alive:
            return False
        return {"game": game, "player": player}


@router.message(F.chat.type == "private", DeadPlayerFilter())
async def on_dead_player_message(message: Message, bot: Bot, game: Game, player: Player, UL=texts) -> None:
    deadline = game.last_word_deadline.get(player.user_id)
    if deadline is not None and time.monotonic() <= deadline:
        if len(message.text) > LAST_WORD_MAX_LENGTH:
            await message.answer(
                UL.LAST_WORD_TOO_LONG.format(length=len(message.text), limit=LAST_WORD_MAX_LENGTH)
            )
            return
        del game.last_word_deadline[player.user_id]
        try:
            await bot.send_message(
                game.chat_id,
                get_texts(game.settings.lang).LAST_WORD_GROUP.format(name=mention(player), text=esc(message.text)),
            )
        except (TelegramBadRequest, TelegramForbiddenError):
            return
        await message.answer(UL.LAST_WORD_SENT)
        return
    game.last_word_deadline.pop(player.user_id, None)

    line = texts.DEAD_CHAT_LINE.format(name=esc(player.full_name), text=esc(message.text))
    for other in game.players.values():
        if not other.alive and other.user_id != player.user_id:
            try:
                await bot.send_message(other.user_id, line)
            except (TelegramBadRequest, TelegramForbiddenError):
                pass
