from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from game.manager import manager
from game.models import GameState
from utils import build_vote_tally_text

router = Router(name="day")


@router.callback_query(F.data.startswith("vote:"))
async def on_vote(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.DAY_VOTING:
        await callback.answer("Hozir ovoz berish vaqti emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive:
        await callback.answer("Siz o'yinda emassiz yoki halok bo'lgansiz.", show_alert=True)
        return

    data = callback.data.split(":", 1)[1]
    target_id = None if data == "skip" else int(data)
    if target_id is not None and (target_id not in game.players or not game.players[target_id].alive):
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    game.day_votes[voter.user_id] = target_id
    await callback.answer("Ovozingiz qabul qilindi ✅")

    if game.vote_message_id:
        try:
            await bot.edit_message_text(
                build_vote_tally_text(game),
                chat_id=game.chat_id,
                message_id=game.vote_message_id,
            )
        except TelegramBadRequest:
            pass

    if len(game.day_votes) >= game.vote_needed and game.vote_event:
        game.vote_event.set()
