from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import texts
from config import ADMIN_IDS, CARD_PAYMENTS_ENABLED, PAYMENT_CARD_HOLDER, PAYMENT_CARD_NUMBER, PAYMENT_CONTACT_USERNAME
from economy import (
    COIN_EXCHANGE_AMOUNTS,
    COIN_TO_DOLLAR_RATE,
    CURRENCY_EMOJI,
    DIAMOND_PACKAGES,
    DIAMOND_TO_DOLLAR_RATE,
    STARS_PACKAGES,
)
from i18n import texts_for_user
from utils import esc

router = Router(name="shop")


def format_som(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def build_shop_keyboard(L=texts) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(DIAMOND_PACKAGES), 2):
        row = [
            InlineKeyboardButton(
                text=L.SHOP_CARD_BUTTON.format(diamonds=amount, price=format_som(price)),
                callback_data=f"shop:buy:{amount}",
            )
            for amount, price in DIAMOND_PACKAGES[i : i + 2]
        ]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def card_payments_available() -> bool:
    return CARD_PAYMENTS_ENABLED and bool(PAYMENT_CARD_NUMBER)


def shop_view(L=texts) -> tuple[str, InlineKeyboardMarkup]:
    """Telegram Stars paketlari birinchi, karta orqali to'lov (yoqilgan bo'lsa) — keyin."""
    stars_buttons = [
        InlineKeyboardButton(
            text=L.SHOP_STARS_BUTTON.format(diamonds=diamonds, stars=stars),
            callback_data=f"stars:buy:{diamonds}",
        )
        for diamonds, stars in STARS_PACKAGES
    ]
    rows = [stars_buttons[i : i + 2] for i in range(0, len(stars_buttons), 2)]
    lines = [L.SHOP_TITLE, "", L.SHOP_STARS_SECTION]
    if card_payments_available():
        rows += build_shop_keyboard(L).inline_keyboard
        lines += ["", L.SHOP_CARD_SECTION]
    lines += ["", L.SHOP_FOOTER]
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("shop", "olmos"))
async def cmd_shop(message: Message, L=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    text, kb = shop_view(L)
    await message.answer(text, reply_markup=kb)


EXCHANGE_AMOUNTS = {amount for amount, _ in DIAMOND_PACKAGES}


def exchange_text(L=texts) -> str:
    return L.EXCHANGE_TEXT.format(diamond_rate=DIAMOND_TO_DOLLAR_RATE, coin_rate=COIN_TO_DOLLAR_RATE)


def build_exchange_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(DIAMOND_PACKAGES), 2):
        row = [
            InlineKeyboardButton(
                text=f"{amount}💎 → {amount * DIAMOND_TO_DOLLAR_RATE}💵",
                callback_data=f"exchange:{amount}",
            )
            for amount, _ in DIAMOND_PACKAGES[i : i + 2]
        ]
        rows.append(row)
    for i in range(0, len(COIN_EXCHANGE_AMOUNTS), 2):
        row = [
            InlineKeyboardButton(
                text=f"{amount}🪙 → {amount * COIN_TO_DOLLAR_RATE}💵",
                callback_data=f"exchange_coin:{amount}",
            )
            for amount in COIN_EXCHANGE_AMOUNTS[i : i + 2]
        ]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("almashtir", "exchange"))
async def cmd_exchange(message: Message, L=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(exchange_text(L), reply_markup=build_exchange_keyboard())


async def _do_exchange(callback: CallbackQuery, UL, column: str, rate: int, allowed: set[int], not_enough: str) -> None:
    raw = callback.data.split(":")[1]
    # Faqat tugmalardagi miqdorlar qabul qilinadi — soxta (manfiy) miqdor yuborib bo'lmaydi.
    if not raw.isdigit() or int(raw) not in allowed:
        await callback.answer(UL.EXCHANGE_BAD_AMOUNT, show_alert=True)
        return
    amount = int(raw)
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    if not await db.spend_balance(callback.from_user.id, column, amount):
        await callback.answer(not_enough, show_alert=True)
        return

    dollars = amount * rate
    emoji = CURRENCY_EMOJI["diamond" if column == "diamonds" else "coin"]
    await db.add_balance(callback.from_user.id, dollars=dollars)
    await callback.answer(UL.EXCHANGE_DONE_SHORT.format(amount=amount, emoji=emoji, dollars=dollars), show_alert=True)
    try:
        await callback.message.edit_text(UL.EXCHANGE_DONE.format(amount=amount, emoji=emoji, dollars=dollars))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("exchange:"))
async def on_exchange(callback: CallbackQuery, UL=texts) -> None:
    await _do_exchange(
        callback, UL, "diamonds", DIAMOND_TO_DOLLAR_RATE, EXCHANGE_AMOUNTS, UL.EXCHANGE_NOT_ENOUGH_DIAMONDS
    )


@router.callback_query(F.data.startswith("exchange_coin:"))
async def on_exchange_coin(callback: CallbackQuery, UL=texts) -> None:
    await _do_exchange(
        callback, UL, "coins", COIN_TO_DOLLAR_RATE, set(COIN_EXCHANGE_AMOUNTS), UL.EXCHANGE_NOT_ENOUGH_COINS
    )


@router.callback_query(F.data.startswith("shop:buy:"))
async def on_buy(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    if not card_payments_available():
        await callback.answer(UL.SHOP_CARD_DISABLED, show_alert=True)
        return

    raw = callback.data.split(":")[2]
    amount = int(raw) if raw.isdigit() else None
    price = next((p for a, p in DIAMOND_PACKAGES if a == amount), None)
    if price is None:
        await callback.answer(UL.PACKAGE_NOT_FOUND, show_alert=True)
        return

    order_id = await db.create_order(callback.from_user.id, amount, price)
    await callback.answer()

    text = UL.CARD_ORDER_TEXT.format(
        diamonds=amount, price=format_som(price), card=PAYMENT_CARD_NUMBER, holder=PAYMENT_CARD_HOLDER, order_id=order_id
    )
    contact_kb = None
    if PAYMENT_CONTACT_USERNAME:
        text += UL.CARD_ORDER_RECEIPT.format(order_id=order_id, contact=PAYMENT_CONTACT_USERNAME)
        contact_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=UL.CARD_RECEIPT_BUTTON, url=f"https://t.me/{PAYMENT_CONTACT_USERNAME}")]
            ]
        )
    try:
        await callback.message.edit_text(text, reply_markup=contact_kb)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=contact_kb)

    for admin_id in ADMIN_IDS:
        AL = await texts_for_user(admin_id)
        admin_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=AL.CARD_APPROVE_BUTTON, callback_data=f"shop:approve:{order_id}"),
                    InlineKeyboardButton(text=AL.CARD_REJECT_BUTTON, callback_data=f"shop:reject:{order_id}"),
                ]
            ]
        )
        admin_text = AL.CARD_ADMIN_ORDER.format(
            order_id=order_id, name=esc(callback.from_user.full_name), user_id=callback.from_user.id,
            diamonds=amount, price=format_som(price),
        )
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=admin_kb)
        except (TelegramForbiddenError, TelegramBadRequest):
            pass


async def _review_order(callback: CallbackQuery, UL):
    """Admin tugmasi uchun umumiy tekshiruvlar; to'g'ri bo'lsa buyurtmani qaytaradi."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(UL.NOT_FOR_YOU, show_alert=True)
        return None
    order = await db.get_order(int(callback.data.split(":")[2]))
    if not order:
        await callback.answer(UL.ORDER_NOT_FOUND, show_alert=True)
        return None
    if order["status"] != "pending":
        await callback.answer(UL.ORDER_ALREADY_REVIEWED, show_alert=True)
        return None
    return order


@router.callback_query(F.data.startswith("shop:approve:"))
async def on_approve(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    order = await _review_order(callback, UL)
    if not order:
        return

    await db.set_order_status(order["order_id"], "approved")
    await db.add_balance(order["user_id"], diamonds=order["amount"])
    await callback.answer(UL.ORDER_APPROVED_ALERT)
    try:
        await callback.message.edit_text(callback.message.text + "\n\n" + UL.ORDER_APPROVED_MARK)
    except TelegramBadRequest:
        pass

    buyer = await texts_for_user(order["user_id"])
    try:
        await bot.send_message(order["user_id"], buyer.ORDER_APPROVED_USER.format(diamonds=order["amount"]))
    except (TelegramForbiddenError, TelegramBadRequest):
        pass


@router.callback_query(F.data.startswith("shop:reject:"))
async def on_reject(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    order = await _review_order(callback, UL)
    if not order:
        return

    await db.set_order_status(order["order_id"], "rejected")
    await callback.answer(UL.ORDER_REJECTED_ALERT)
    try:
        await callback.message.edit_text(callback.message.text + "\n\n" + UL.ORDER_REJECTED_MARK)
    except TelegramBadRequest:
        pass

    buyer = await texts_for_user(order["user_id"])
    try:
        await bot.send_message(order["user_id"], buyer.ORDER_REJECTED_USER.format(order_id=order["order_id"]))
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
