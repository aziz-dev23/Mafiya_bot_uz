from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import texts
from config import ADMIN_IDS
from economy import CURRENCY_COLUMN, CURRENCY_EMOJI, TRANSFER_DAILY_LIMITS, TRANSFER_MIN_GAMES
from i18n import texts_for_user
from utils import esc

router = Router(name="transfer")


class Transfer(StatesGroup):
    recipient = State()
    amount = State()
    confirm = State()


async def _limit_error(user_id: int, currency: str, amount: int = 0, L=texts) -> str | None:
    """Cheklovga tushsa xato matnini qaytaradi. ADMIN_IDS ga cheklov qo'yilmaydi."""
    if user_id in ADMIN_IDS:
        return None
    row = await db.get_user(user_id)
    played = row["games"] if row else 0
    if played < TRANSFER_MIN_GAMES:
        return L.TRANSFER_MIN_GAMES_REQUIRED.format(required=TRANSFER_MIN_GAMES, played=played)
    limit = TRANSFER_DAILY_LIMITS[currency]
    sent = await db.sent_today(user_id, currency)
    if sent + amount > limit:
        return L.TRANSFER_DAILY_LIMIT_EXCEEDED.format(
            limit=limit, sent=sent, left=max(0, limit - sent), emoji=CURRENCY_EMOJI[currency]
        )
    return None


async def _start_transfer(message: Message, state: FSMContext, currency: str, user, L=texts) -> None:
    await db.ensure_user(user.id, user.full_name, user.username)
    await state.clear()
    error = await _limit_error(user.id, currency, L=L)
    if error:
        await message.answer(error)
        return
    await state.update_data(currency=currency)
    await state.set_state(Transfer.recipient)
    await message.answer(L.TRANSFER_START.format(currency=L.CURRENCY_LABELS[currency]))


@router.message(Command("send", "sendgem"), F.chat.type != "private")
async def cmd_send_in_group(message: Message, UL=texts) -> None:
    # Guruhda boshlansa, bot shu odamning keyingi har bir guruh xabarini qabul qiluvchi deb o'qib qolardi.
    await message.answer(UL.TRANSFER_PRIVATE_ONLY)


@router.message(Command("send"), F.chat.type == "private")
async def cmd_send_dollar(message: Message, state: FSMContext, L=texts) -> None:
    await _start_transfer(message, state, "dollar", message.from_user, L)


@router.message(Command("sendgem"), F.chat.type == "private")
async def cmd_send_diamond(message: Message, state: FSMContext, L=texts) -> None:
    await _start_transfer(message, state, "diamond", message.from_user, L)


@router.callback_query(F.data == "menu:send_dollar")
async def on_menu_send_dollar(callback: CallbackQuery, state: FSMContext, UL=texts) -> None:
    await callback.answer()
    await _start_transfer(callback.message, state, "dollar", callback.from_user, UL)


@router.callback_query(F.data == "menu:send_diamond")
async def on_menu_send_diamond(callback: CallbackQuery, state: FSMContext, UL=texts) -> None:
    await callback.answer()
    await _start_transfer(callback.message, state, "diamond", callback.from_user, UL)


@router.message(Transfer.recipient, F.chat.type == "private")
async def on_recipient(message: Message, state: FSMContext, L=texts) -> None:
    raw = (message.text or "").strip().lstrip("@")

    recipient_row = await db.get_user(int(raw)) if raw.isdigit() else await db.get_user_by_username(raw)
    if not recipient_row:
        await message.answer(L.TRANSFER_USER_NOT_FOUND)
        return

    if recipient_row["user_id"] == message.from_user.id:
        await message.answer(L.TRANSFER_SELF)
        return

    await state.update_data(recipient_id=recipient_row["user_id"], recipient_name=recipient_row["full_name"])
    await state.set_state(Transfer.amount)
    await message.answer(L.TRANSFER_ASK_AMOUNT.format(name=esc(recipient_row["full_name"])))


@router.message(Transfer.amount, F.chat.type == "private")
async def on_amount(message: Message, state: FSMContext, L=texts) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(L.TRANSFER_BAD_AMOUNT)
        return

    amount = int(raw)
    data = await state.get_data()
    currency = data["currency"]
    col = CURRENCY_COLUMN[currency]

    sender_row = await db.get_user(message.from_user.id)
    if not sender_row or sender_row[col] < amount:
        await message.answer(L.NOT_ENOUGH_BALANCE.format(emoji=CURRENCY_EMOJI[currency]))
        return
    error = await _limit_error(message.from_user.id, currency, amount, L)
    if error:
        await message.answer(error)
        return

    await state.update_data(amount=amount)
    await state.set_state(Transfer.confirm)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=L.TRANSFER_CONFIRM_BUTTON, callback_data="transfer:confirm"),
                InlineKeyboardButton(text=L.TRANSFER_CANCEL_BUTTON, callback_data="transfer:cancel"),
            ]
        ]
    )
    await message.answer(
        L.TRANSFER_CONFIRM.format(name=esc(data["recipient_name"]), amount=amount, emoji=CURRENCY_EMOJI[currency]),
        reply_markup=kb,
    )


@router.callback_query(F.data == "transfer:cancel", Transfer.confirm)
async def on_transfer_cancel(callback: CallbackQuery, state: FSMContext, UL=texts) -> None:
    await state.clear()
    await callback.answer(UL.TRANSFER_CANCELLED_ALERT)
    try:
        await callback.message.edit_text(UL.TRANSFER_CANCELLED)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "transfer:confirm", Transfer.confirm)
async def on_transfer_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, UL=texts) -> None:
    data = await state.get_data()
    # Holat darhol tozalanadi: "Tasdiqlash" ikki marta tez bosilsa, ikkinchisi endi Transfer.confirm
    # holatiga mos kelmaydi va pul ikki marta yuborilmaydi.
    await state.clear()
    currency = data["currency"]
    amount = data["amount"]
    recipient_id = data["recipient_id"]
    recipient_name = data["recipient_name"]
    col = CURRENCY_COLUMN[currency]
    emoji = CURRENCY_EMOJI[currency]

    error = await _limit_error(callback.from_user.id, currency, amount, UL)
    if error:
        await callback.answer(error, show_alert=True)
        return
    if not await db.transfer_balance(callback.from_user.id, recipient_id, currency, col, amount):
        await callback.answer(UL.TRANSFER_NOT_ENOUGH, show_alert=True)
        return

    await callback.answer(UL.TRANSFER_SENT_ALERT)
    try:
        await callback.message.edit_text(UL.TRANSFER_SENT.format(name=esc(recipient_name), amount=amount, emoji=emoji))
    except TelegramBadRequest:
        pass

    recipient_texts = await texts_for_user(recipient_id)
    try:
        await bot.send_message(
            recipient_id,
            recipient_texts.TRANSFER_RECEIVED.format(name=esc(callback.from_user.full_name), amount=amount, emoji=emoji),
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
