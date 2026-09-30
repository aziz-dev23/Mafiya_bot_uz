from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

import texts
from game.engine import announce, confirm_counts, gt
from game.manager import manager
from game.models import GameState
from utils import build_confirm_keyboard, build_vote_keyboard, esc

router = Router(name="day")


@router.callback_query(F.data.startswith("vote:"))
async def on_vote(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.DAY_VOTING:
        await callback.answer(UL.NOT_VOTING_TIME, show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive:
        await callback.answer(UL.NOT_IN_GAME_OR_DEAD, show_alert=True)
        return

    data = callback.data.split(":", 1)[1]
    target_id = None if data == "skip" else int(data)
    if target_id is not None and (target_id not in game.players or not game.players[target_id].alive):
        await callback.answer(UL.PLAYER_NOT_AVAILABLE, show_alert=True)
        return

    changed = voter.user_id in game.day_votes
    if changed and game.day_votes[voter.user_id] == target_id:
        await callback.answer(UL.VOTE_ALREADY)
        return

    game.day_votes[voter.user_id] = target_id
    target_name = UL.VOTE_SKIP_NAME if target_id is None else esc(game.players[target_id].full_name)
    await callback.answer(UL.VOTE_ACCEPTED)
    try:
        # Tugmalar qoladi — vaqt tugaguncha tanlovni o'zgartirish mumkin.
        await callback.message.edit_text(
            UL.VOTE_CHOSEN.format(name=target_name), reply_markup=build_vote_keyboard(game, voter.lang)
        )
    except TelegramBadRequest:
        pass

    G = gt(game)
    name = esc(voter.full_name)
    if not game.settings.open_votes:
        if not changed:
            announce(bot, game, G.VOTE_ANNOUNCE_ANON)
    elif target_id is None:
        announce(bot, game, G.VOTE_ANNOUNCE_SKIP.format(voter=name))
    elif changed:
        announce(bot, game, G.VOTE_ANNOUNCE_CHANGED.format(voter=name, target=target_name))
    else:
        announce(bot, game, G.VOTE_ANNOUNCE.format(voter=name, target=target_name))

    if len(game.day_votes) >= game.vote_needed and game.vote_event:
        game.vote_event.set()


@router.callback_query(F.data.startswith("confirm:"))
async def on_confirm(callback: CallbackQuery, UL=texts) -> None:
    game = manager.get_game(callback.message.chat.id)
    if not game or game.state != GameState.DAY_CONFIRM or game.confirm_candidate is None:
        await callback.answer(UL.NOT_VOTING_TIME, show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive:
        await callback.answer(UL.NOT_IN_GAME_OR_DEAD, show_alert=True)
        return
    if voter.user_id == game.confirm_candidate:
        await callback.answer(UL.CONFIRM_SELF, show_alert=True)
        return

    like = callback.data == "confirm:yes"
    if game.confirm_votes.get(voter.user_id) == like:
        await callback.answer(UL.VOTE_ALREADY)
        return

    game.confirm_votes[voter.user_id] = like
    await callback.answer(UL.CONFIRM_YES if like else UL.CONFIRM_NO)
    try:
        await callback.message.edit_reply_markup(reply_markup=build_confirm_keyboard(*confirm_counts(game)))
    except TelegramBadRequest:
        pass

    if len(game.confirm_votes) >= game.confirm_needed and game.confirm_event:
        game.confirm_event.set()
