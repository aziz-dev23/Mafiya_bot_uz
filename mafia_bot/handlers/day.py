from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from game.engine import confirm_counts
from game.manager import manager
from game.models import GameState
from utils import build_confirm_keyboard

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
    target_name = "Ovoz bermaslik" if target_id is None else game.players[target_id].full_name
    await callback.answer("Ovozingiz qabul qilindi ✅")
    try:
        await callback.message.edit_text(f"🗳 Siz tanladingiz: {target_name}")
    except TelegramBadRequest:
        pass

    if target_id is None:
        await bot.send_message(game.chat_id, f"🔵 {voter.full_name} — ovoz bermaslikni tanladi.")
    else:
        await bot.send_message(game.chat_id, f"🔵 {voter.full_name} — {target_name}ga ovoz berdi.")

    if len(game.day_votes) >= game.vote_needed and game.vote_event:
        game.vote_event.set()


@router.callback_query(F.data.startswith("confirm:"))
async def on_confirm(callback: CallbackQuery) -> None:
    game = manager.get_game(callback.message.chat.id)
    if not game or game.state != GameState.DAY_CONFIRM:
        await callback.answer("Hozir ovoz berish vaqti emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive:
        await callback.answer("Siz o'yinda emassiz yoki halok bo'lgansiz.", show_alert=True)
        return
    if voter.user_id == game.confirm_candidate:
        await callback.answer("O'zingiz uchun ovoz bera olmaysiz.", show_alert=True)
        return

    like = callback.data == "confirm:yes"
    if game.confirm_votes.get(voter.user_id) == like:
        await callback.answer("Ovozingiz allaqachon qabul qilingan.")
        return

    game.confirm_votes[voter.user_id] = like
    await callback.answer("👍 Ha" if like else "👎 Yo'q")
    try:
        await callback.message.edit_reply_markup(reply_markup=build_confirm_keyboard(*confirm_counts(game)))
    except TelegramBadRequest:
        pass

    if len(game.confirm_votes) >= game.confirm_needed and game.confirm_event:
        game.confirm_event.set()
