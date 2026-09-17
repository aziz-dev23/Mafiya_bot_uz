from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

import db
from game.engine import night_all_done
from game.manager import manager
from game.models import GameState, Role
from utils import build_mafia_kill_keyboard

router = Router(name="night")


@router.callback_query(F.data.startswith("m_kill:"))
async def on_mafia_kill(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role not in (Role.MAFIA, Role.DON):
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

    if len(game.mafia_votes) == game.night_mafia_needed:
        await bot.send_message(game.chat_id, "🔪 Mafiya o'ljasini tanladi.")

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data == "m_rifle_toggle")
async def on_rifle_toggle(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    mafia = game.players.get(callback.from_user.id)
    if (
        not mafia
        or not mafia.alive
        or mafia.role not in (Role.MAFIA, Role.DON)
        or mafia.items.get("rifle", 0) <= 0
    ):
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    if callback.from_user.id in game.mafia_rifle_users:
        game.mafia_rifle_users.discard(callback.from_user.id)
        await callback.answer("Miltiq o'chirildi.")
    else:
        game.mafia_rifle_users.add(callback.from_user.id)
        await callback.answer("Miltiq yoqildi — himoyani bekor qiladi!")

    mafia_ids = {p.user_id for p in game.players.values() if p.alive and p.role in (Role.MAFIA, Role.DON)}
    try:
        await callback.message.edit_reply_markup(
            reply_markup=build_mafia_kill_keyboard(game, callback.from_user.id, mafia_ids)
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("d_save:"))
async def on_doctor_save(callback: CallbackQuery, bot: Bot) -> None:
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

    first_time = not game.doctor_acted
    game.doctor_target = target_id
    game.doctor_acted = True
    await callback.answer(f"Siz {target.full_name}ni himoya qilyapsiz.")
    try:
        await callback.message.edit_text(f"💊 Siz himoya qildingiz: {target.full_name}")
    except TelegramBadRequest:
        pass

    if first_time:
        await bot.send_message(game.chat_id, "💊 Doktor tungi navbatchilikka ketdi.")

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("c_check:"))
async def on_detective_check(callback: CallbackQuery, bot: Bot) -> None:
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

    first_time = not game.detective_acted
    game.detective_target = target_id
    game.detective_acted = True

    faked = False
    if target.items.get("fake_doc", 0) > 0 and await db.consume_item(target.user_id, "fake_doc"):
        target.items["fake_doc"] -= 1
        faked = True
    if target.user_id == game.advokat_target:
        faked = True

    is_mafia = target.role in (Role.MAFIA, Role.DON) and not faked
    if is_mafia:
        game.detective_correct = True
    result = "u — Mafiya a'zosi! 🔪" if is_mafia else "u — mafiya emas. ✅"

    await callback.answer()
    try:
        await callback.message.edit_text(f"🕵️ Tekshiruv natijasi: {target.full_name} — {result}")
    except TelegramBadRequest:
        pass

    if first_time:
        await bot.send_message(game.chat_id, "🕵️ Komissar tekshiruvini boshladi.")

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("q_kill:"))
async def on_killer_kill(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.KILLER:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    first_time = not game.killer_acted
    game.killer_target = target_id
    game.killer_acted = True
    await callback.answer(f"Siz {target.full_name}ni tanladingiz.")
    try:
        await callback.message.edit_text(f"🔪 Siz tanladingiz: {target.full_name}")
    except TelegramBadRequest:
        pass

    if first_time:
        await bot.send_message(game.chat_id, "🔪 Qotil nishonini tanladi.")

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("yq_kill:"))
async def on_hitman_kill(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.HITMAN:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    first_time = not game.hitman_acted
    game.hitman_target = target_id
    game.hitman_acted = True
    await callback.answer(f"Siz {target.full_name}ni tanladingiz.")
    try:
        await callback.message.edit_text(f"🥷 Siz tanladingiz: {target.full_name}")
    except TelegramBadRequest:
        pass

    if first_time:
        await bot.send_message(game.chat_id, "🥷 Yollanma qotil nishonini tanladi.")

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("kez_dose:"))
async def on_poisoner_dose(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.POISONER:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    first_time = not game.poisoner_acted
    game.poisoner_acted = True
    if target.items.get("poison_shield", 0) > 0 and await db.consume_item(target.user_id, "poison_shield"):
        target.items["poison_shield"] -= 1
        # Kezuvchi natijani bilmaydi — himoya sezilmasdan sarflanadi, dori ta'sirsiz qoladi.
    else:
        game.pending_poison[target_id] = game.day_number + 1

    await callback.answer(f"Siz {target.full_name}ga dori berdingiz.")
    try:
        await callback.message.edit_text(f"💊 Siz dori berdingiz: {target.full_name}")
    except TelegramBadRequest:
        pass

    if first_time:
        await bot.send_message(game.chat_id, "💊 Kezuvchi kimgadir dori berdi.")

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("daydi_visit:"))
async def on_wanderer_visit(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.WANDERER:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    first_time = not game.wanderer_acted
    game.wanderer_target = target_id
    game.wanderer_acted = True
    await callback.answer(f"Siz {target.full_name}ning oldiga bordingiz.")
    try:
        await callback.message.edit_text(f"🚶 Siz tashrif buyurdingiz: {target.full_name}")
    except TelegramBadRequest:
        pass

    if first_time:
        await bot.send_message(game.chat_id, "🚶 Daydi kimningdir oldiga bordi.")

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("don_check:"))
async def on_don_check(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.DON:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return
    if game.don_check_used:
        await callback.answer("Siz bu imkoniyatdan allaqachon foydalangansiz.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    game.don_check_used = True
    is_detective = target.role == Role.DETECTIVE
    result = "u — Komissar! 🕵️" if is_detective else "u — komissar emas."

    await callback.answer()
    try:
        await callback.message.edit_text(f"🎩 Aniqlash natijasi: {target.full_name} — {result}")
    except TelegramBadRequest:
        pass

    await bot.send_message(game.chat_id, "🎩 Don o'z tekshiruvini o'tkazdi.")


@router.callback_query(F.data.startswith("hero_shot:"))
async def on_hero_shot(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.DAWN:
        await callback.answer("Hozir tong emas.", show_alert=True)
        return

    shooter = game.players.get(callback.from_user.id)
    if not shooter or not shooter.alive or shooter.items.get("hero_shot", 0) <= 0:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    game.dawn_shots[callback.from_user.id] = target_id
    game.dawn_acted.add(callback.from_user.id)
    await callback.answer(f"Siz {target.full_name}ni otishga qaror qildingiz.")
    try:
        await callback.message.edit_text(f"🥷 Siz otishga qaror qildingiz: {target.full_name}")
    except TelegramBadRequest:
        pass

    if len(game.dawn_acted) >= game.dawn_needed and game.dawn_event:
        game.dawn_event.set()


@router.callback_query(F.data.startswith("advokat_shield:"))
async def on_advokat_shield(callback: CallbackQuery, bot: Bot) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return

    voter = game.players.get(callback.from_user.id)
    if not voter or not voter.alive or voter.role != Role.LAWYER:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    first_time = not game.advokat_acted
    game.advokat_target = target_id
    game.advokat_acted = True
    await callback.answer(f"Siz {target.full_name}ni himoya qilyapsiz.")
    try:
        await callback.message.edit_text(f"👨‍💼 Siz himoya qildingiz: {target.full_name}")
    except TelegramBadRequest:
        pass

    if first_time:
        await bot.send_message(game.chat_id, "👨‍💼 Advokat o'z himoyasini tayinladi.")

    if night_all_done(game) and game.night_event:
        game.night_event.set()


@router.callback_query(F.data.startswith("sorcerer_revenge:"))
async def on_sorcerer_revenge(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.revenge_event is None:
        await callback.answer("Bu imkoniyat endi mavjud emas.", show_alert=True)
        return

    sorcerer = game.players.get(callback.from_user.id)
    if not sorcerer or sorcerer.role != Role.SORCERER:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    target_id = int(callback.data.split(":", 1)[1])
    target = game.players.get(target_id)
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return

    game.revenge_target = target_id
    await callback.answer(f"O'ch: {target.full_name}")
    try:
        await callback.message.edit_text(f"🧞‍♂️ O'ch tanlandi: {target.full_name}")
    except TelegramBadRequest:
        pass

    game.revenge_event.set()
