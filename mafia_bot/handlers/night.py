from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

import db
from game.engine import night_all_done
from game.manager import manager
from game.models import GameState, Role
from utils import build_mafia_kill_keyboard

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


@router.callback_query(F.data == "m_rifle_toggle")
async def on_rifle_toggle(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    mafia = game.players.get(callback.from_user.id)
    if not mafia or not mafia.alive or mafia.role != Role.MAFIA or mafia.items.get("rifle", 0) <= 0:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    if callback.from_user.id in game.mafia_rifle_users:
        game.mafia_rifle_users.discard(callback.from_user.id)
        await callback.answer("Miltiq o'chirildi.")
    else:
        game.mafia_rifle_users.add(callback.from_user.id)
        await callback.answer("Miltiq yoqildi — himoyani bekor qiladi!")

    mafia_ids = {p.user_id for p in game.players.values() if p.alive and p.role == Role.MAFIA}
    try:
        await callback.message.edit_reply_markup(
            reply_markup=build_mafia_kill_keyboard(game, callback.from_user.id, mafia_ids)
        )
    except TelegramBadRequest:
        pass


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

    faked = False
    if target.items.get("fake_doc", 0) > 0 and await db.consume_item(target.user_id, "fake_doc"):
        target.items["fake_doc"] -= 1
        faked = True

    is_mafia = target.role == Role.MAFIA and not faked
    if is_mafia:
        game.detective_correct = True
    result = "u — Mafiya a'zosi! 🔪" if is_mafia else "u — mafiya emas. ✅"

    await callback.answer()
    try:
        await callback.message.edit_text(f"🕵️ Tekshiruv natijasi: {target.full_name} — {result}")
    except TelegramBadRequest:
        pass

    if night_all_done(game) and game.night_event:
        game.night_event.set()
