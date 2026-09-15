from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from game.engine import night_all_done
from game.manager import manager
from game.models import GameState, Role

router = Router(name="night")


@router.callback_query(F.data.startswith("m_kill:"))
async def on_mafia_kill(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.MAFIA:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    game.mafia_votes[voter.user_id] = target_id
    await callback.answer(f"Siz {target.full_name}ni tanladingiz.")
    try:
        await callback.message.edit_text(
            f"🔪 Siz tanladingiz: {target.full_name}\nBoshqa mafiyalarni kutmoqdamiz..."
        )
    except TelegramBadRequest:
        pass

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("d_save:"))
async def on_doctor_save(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.DOCTOR:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    game.doctor_target = target_id
    game.doctor_acted = True
    await callback.answer(f"Siz {target.full_name}ni himoya qilyapsiz.")
    try:
        await callback.message.edit_text(f"💊 Siz himoya qildingiz: {target.full_name}")
    except TelegramBadRequest:
        pass

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("c_check:"))
async def on_detective_check(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.DETECTIVE:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    game.detective_target = target_id
    game.detective_acted = True
    is_mafia = target.role == Role.MAFIA
    result = "u — Mafiya a'zosi! 🔪" if is_mafia else "u — mafiya emas. ✅"

    await callback.answer()
    try:
        await callback.message.edit_text(f"🕵️ Tekshiruv natijasi: {target.full_name} — {result}")
    except TelegramBadRequest:
        pass

    if night_all_done(game) and game.night_event:
        game.night_event.set()
