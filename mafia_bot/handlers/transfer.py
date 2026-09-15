from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from economy import CURRENCY_COLUMN, CURRENCY_EMOJI

router = Router(name="transfer")

CURRENCY_LABELS = {"dollar": "Dollar 💵", "diamond": "Olmos 💎"}


class Transfer(StatesGroup):
    recipient = State()
    amount = State()
    confirm = State()


async def _start_transfer(message: Message, state: FSMContext, currency: str) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await state.clear()
    await state.update_data(currency=currency)
    await state.set_state(Transfer.recipient)
    await message.answer(
        f"{CURRENCY_LABELS[currency]} yubormoqchisiz.\n\n"
        "Kimga yuborasiz? Qabul qiluvchining foydalanuvchi ID raqami yoki @username'ini yuboring.\n"
        "(Qabul qiluvchi avval botga /start bosgan bo'lishi kerak.)"
    )


@router.message(Command("send"))
async def cmd_send_dollar(message: Message, state: FSMContext) -> None:
    await _start_transfer(message, state, "dollar")


@router.message(Command("sendgem"))
async def cmd_send_diamond(message: Message, state: FSMContext) -> None:
    await _start_transfer(message, state, "diamond")


@router.callback_query(F.data == "menu:send_dollar")
async def on_menu_send_dollar(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _start_transfer(callback.message, state, "dollar")


@router.callback_query(F.data == "menu:send_diamond")
async def on_menu_send_diamond(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _start_transfer(callback.message, state, "diamond")


@router.message(Transfer.recipient)
async def on_recipient(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().lstrip("@")

    recipient_row = await db.get_user(int(raw)) if raw.isdigit() else await db.get_user_by_username(raw)
    if not recipient_row:
        await message.answer(
            "Bunday foydalanuvchi topilmadi — u botga hali /start bosmagan bo'lishi mumkin.\n"
            "Qaytadan ID yoki @username yuboring."
        )
        return

    if recipient_row["user_id"] == message.from_user.id:
        await message.answer("O'zingizga yubora olmaysiz. Boshqa foydalanuvchi ID/username yuboring.")
        return

    await state.update_data(recipient_id=recipient_row["user_id"], recipient_name=recipient_row["full_name"])
    await state.set_state(Transfer.amount)
    await message.answer(f"Qabul qiluvchi: <b>{recipient_row['full_name']}</b>\nEndi miqdorni kiriting (butun son):")


@router.message(Transfer.amount)
async def on_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("Miqdor musbat butun son bo'lishi kerak. Qaytadan kiriting:")
        return

    amount = int(raw)
    data = await state.get_data()
    currency = data["currency"]
    col = CURRENCY_COLUMN[currency]

    sender_row = await db.get_user(message.from_user.id)
    if not sender_row or sender_row[col] < amount:
        await message.answer(f"Balansingizda yetarli {CURRENCY_EMOJI[currency]} yo'q.")
        return

    await state.update_data(amount=amount)
    await state.set_state(Transfer.confirm)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="transfer:confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="transfer:cancel"),
            ]
        ]
    )
    await message.answer(
        f"<b>{data['recipient_name']}</b>ga {amount}{CURRENCY_EMOJI[currency]} yubormoqchisiz. Tasdiqlaysizmi?",
        reply_markup=kb,
    )


@router.callback_query(F.data == "transfer:cancel", Transfer.confirm)
async def on_transfer_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Bekor qilindi.")
    try:
        await callback.message.edit_text("❌ Pul/olmos o'tkazish bekor qilindi.")
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "transfer:confirm", Transfer.confirm)
async def on_transfer_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    currency = data["currency"]
    amount = data["amount"]
    recipient_id = data["recipient_id"]
    recipient_name = data["recipient_name"]
    col = CURRENCY_COLUMN[currency]

    sender_row = await db.get_user(callback.from_user.id)
    if not sender_row or sender_row[col] < amount:
        await callback.answer("Balansingiz yetarli emas.", show_alert=True)
        await state.clear()
        return

    await db.add_balance(callback.from_user.id, **{col: -amount})
    await db.add_balance(recipient_id, **{col: amount})
    await state.clear()

    await callback.answer("Yuborildi ✅")
    try:
        await callback.message.edit_text(f"✅ {recipient_name}ga {amount}{CURRENCY_EMOJI[currency]} yuborildi.")
    except TelegramBadRequest:
        pass

    try:
        await bot.send_message(
            recipient_id,
            f"💌 Sizga <b>{callback.from_user.full_name}</b> tomonidan "
            f"{amount}{CURRENCY_EMOJI[currency]} yuborildi!",
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
