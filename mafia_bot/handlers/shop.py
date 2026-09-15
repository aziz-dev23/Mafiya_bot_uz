from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from config import ADMIN_IDS, PAYMENT_CARD_HOLDER, PAYMENT_CARD_NUMBER
from economy import DIAMOND_PACKAGES

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


@router.message(Command("shop", "olmos"))
async def cmd_shop(message: Message) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    if not PAYMENT_CARD_NUMBER:
        await message.answer("Hozircha olmos sotib olish ishlamayapti, keyinroq urinib ko'ring.")
        return
    await message.answer(
        "💎 <b>OLMOS DO'KONI</b>\nKerakli paketni tanlang:",
        reply_markup=build_shop_keyboard(),
    )


@router.callback_query(F.data.startswith("shop:buy:"))
async def on_buy(callback: CallbackQuery, bot: Bot) -> None:
    if not PAYMENT_CARD_NUMBER:
        await callback.answer("Hozircha ishlamayapti.", show_alert=True)
        return

    amount = int(callback.data.split(":")[2])
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
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        await callback.message.answer(text)

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
        f"Foydalanuvchi: {callback.from_user.full_name} (id=<code>{callback.from_user.id}</code>)\n"
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
