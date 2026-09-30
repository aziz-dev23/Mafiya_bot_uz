from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from config import ADMIN_IDS, CARD_PAYMENTS_ENABLED, PAYMENT_CARD_HOLDER, PAYMENT_CARD_NUMBER, PAYMENT_CONTACT_USERNAME
import texts
from economy import (
    COIN_EXCHANGE_AMOUNTS,
    COIN_TO_DOLLAR_RATE,
    CURRENCY_EMOJI,
    DIAMOND_PACKAGES,
    DIAMOND_TO_DOLLAR_RATE,
    STARS_PACKAGES,
)
from utils import esc

router = Router(name="shop")


def format_som(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def build_shop_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(DIAMOND_PACKAGES), 2):
        row = [
            InlineKeyboardButton(
                text=f"{amount}💎 — {format_som(price)} so'm",
                callback_data=f"shop:buy:{amount}",
            )
            for amount, price in DIAMOND_PACKAGES[i : i + 2]
        ]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def card_payments_available() -> bool:
    return CARD_PAYMENTS_ENABLED and bool(PAYMENT_CARD_NUMBER)


def shop_view() -> tuple[str, InlineKeyboardMarkup]:
    """Telegram Stars paketlari birinchi, karta orqali to'lov (yoqilgan bo'lsa) — keyin."""
    stars_buttons = [
        InlineKeyboardButton(
            text=texts.SHOP_STARS_BUTTON.format(diamonds=diamonds, stars=stars),
            callback_data=f"stars:buy:{diamonds}",
        )
        for diamonds, stars in STARS_PACKAGES
    ]
    rows = [stars_buttons[i : i + 2] for i in range(0, len(stars_buttons), 2)]
    lines = [texts.SHOP_TITLE, "", texts.SHOP_STARS_SECTION]
    if card_payments_available():
        rows += build_shop_keyboard().inline_keyboard
        lines += ["", texts.SHOP_CARD_SECTION]
    lines += ["", texts.SHOP_FOOTER]
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("shop", "olmos"))
async def cmd_shop(message: Message) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    text, kb = shop_view()
    await message.answer(text, reply_markup=kb)


EXCHANGE_AMOUNTS = {amount for amount, _ in DIAMOND_PACKAGES}


def exchange_text() -> str:
    return texts.EXCHANGE_TEXT.format(diamond_rate=DIAMOND_TO_DOLLAR_RATE, coin_rate=COIN_TO_DOLLAR_RATE)


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
async def cmd_exchange(message: Message) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(exchange_text(), reply_markup=build_exchange_keyboard())


async def _do_exchange(callback: CallbackQuery, column: str, rate: int, allowed: set[int], not_enough: str) -> None:
    raw = callback.data.split(":")[1]
    # Faqat tugmalardagi miqdorlar qabul qilinadi — soxta (manfiy) miqdor yuborib bo'lmaydi.
    if not raw.isdigit() or int(raw) not in allowed:
        await callback.answer(texts.EXCHANGE_BAD_AMOUNT, show_alert=True)
        return
    amount = int(raw)
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    if not await db.spend_balance(callback.from_user.id, column, amount):
        await callback.answer(not_enough, show_alert=True)
        return

    dollars = amount * rate
    emoji = CURRENCY_EMOJI["diamond" if column == "diamonds" else "coin"]
    await db.add_balance(callback.from_user.id, dollars=dollars)
    await callback.answer(texts.EXCHANGE_DONE_SHORT.format(amount=amount, emoji=emoji, dollars=dollars), show_alert=True)
    try:
        await callback.message.edit_text(texts.EXCHANGE_DONE.format(amount=amount, emoji=emoji, dollars=dollars))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("exchange:"))
async def on_exchange(callback: CallbackQuery) -> None:
    await _do_exchange(
        callback, "diamonds", DIAMOND_TO_DOLLAR_RATE, EXCHANGE_AMOUNTS, texts.EXCHANGE_NOT_ENOUGH_DIAMONDS
    )


@router.callback_query(F.data.startswith("exchange_coin:"))
async def on_exchange_coin(callback: CallbackQuery) -> None:
    await _do_exchange(
        callback, "coins", COIN_TO_DOLLAR_RATE, set(COIN_EXCHANGE_AMOUNTS), texts.EXCHANGE_NOT_ENOUGH_COINS
    )


@router.callback_query(F.data.startswith("shop:buy:"))
async def on_buy(callback: CallbackQuery, bot: Bot) -> None:
    if not card_payments_available():
        await callback.answer(texts.SHOP_CARD_DISABLED, show_alert=True)
        return

    raw = callback.data.split(":")[2]
    amount = int(raw) if raw.isdigit() else None
    price = next((p for a, p in DIAMOND_PACKAGES if a == amount), None)
    if price is None:
        await callback.answer("Bu paket topilmadi.", show_alert=True)
        return

    order_id = await db.create_order(callback.from_user.id, amount, price)
    await callback.answer()

    text = (
        f"💎 <b>{amount} Olmos xaridi</b>\n\n"
        f"To'lov summasi: <b>{format_som(price)} so'm</b>\n\n"
        f"Karta raqami: <code>{PAYMENT_CARD_NUMBER}</code>\n"
        f"Karta egasi: {PAYMENT_CARD_HOLDER}\n\n"
        "⚠️ <b>DIQQAT!</b> To'lovni amalga oshirayotganda <b>IZOH</b> qismiga "
        f"faqat ushbu buyurtma raqamini yozing:\n\n<code>#{order_id}</code>\n\n"
        "To'lov qilgach kuting — administrator tekshirib, olmoslarni hisobingizga "
        "qo'shadi."
    )
    contact_kb = None
    if PAYMENT_CONTACT_USERNAME:
        text += (
            f"\n\n🧾 To'lovdan so'ng <b>chekni (skrinshot)</b> buyurtma raqami "
            f"<code>#{order_id}</code> bilan birga @{PAYMENT_CONTACT_USERNAME} ga yuboring."
        )
        contact_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🧾 Chekni yuborish", url=f"https://t.me/{PAYMENT_CONTACT_USERNAME}")]
            ]
        )
    try:
        await callback.message.edit_text(text, reply_markup=contact_kb)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=contact_kb)

    if not ADMIN_IDS:
        return

    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"shop:approve:{order_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"shop:reject:{order_id}"),
            ]
        ]
    )
    admin_text = (
        f"🧾 <b>Yangi buyurtma #{order_id}</b>\n"
        f"Foydalanuvchi: {esc(callback.from_user.full_name)} (id=<code>{callback.from_user.id}</code>)\n"
        f"Paket: {amount}💎 — {format_som(price)} so'm\n\n"
        "To'lov tushganini tekshirib, tugmalardan birini bosing."
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=admin_kb)
        except (TelegramForbiddenError, TelegramBadRequest):
            pass


@router.callback_query(F.data.startswith("shop:approve:"))
async def on_approve(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    order_id = int(callback.data.split(":")[2])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    if order["status"] != "pending":
        await callback.answer("Bu buyurtma allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.set_order_status(order_id, "approved")
    await db.add_balance(order["user_id"], diamonds=order["amount"])
    await callback.answer("Tasdiqlandi ✅")

    try:
        await callback.message.edit_text(callback.message.text + "\n\n✅ Tasdiqlandi va olmos berildi.")
    except TelegramBadRequest:
        pass

    try:
        await bot.send_message(
            order["user_id"],
            f"✅ To'lovingiz tasdiqlandi! {order['amount']}💎 hisobingizga qo'shildi.",
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass


@router.callback_query(F.data.startswith("shop:reject:"))
async def on_reject(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    order_id = int(callback.data.split(":")[2])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    if order["status"] != "pending":
        await callback.answer("Bu buyurtma allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.set_order_status(order_id, "rejected")
    await callback.answer("Rad etildi ❌")

    try:
        await callback.message.edit_text(callback.message.text + "\n\n❌ Rad etildi.")
    except TelegramBadRequest:
        pass

    try:
        await bot.send_message(
            order["user_id"],
            f"❌ Buyurtma #{order_id} rad etildi. Savol bo'lsa administratorga murojaat qiling.",
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
