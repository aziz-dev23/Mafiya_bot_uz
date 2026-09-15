from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from config import SELLER_IDS
from economy import CURRENCY_COLUMN, CURRENCY_EMOJI, parse_currency

router = Router(name="market")


def listing_line(listing) -> str:
    return (
        f"#{listing['listing_id']}: {listing['sell_amount']}{CURRENCY_EMOJI[listing['sell_currency']]} "
        f"→ {listing['price_amount']}{CURRENCY_EMOJI[listing['price_currency']]}"
    )


@router.message(Command("sell"))
async def cmd_sell(message: Message) -> None:
    if message.from_user.id not in SELLER_IDS:
        return

    parts = message.text.split()
    if len(parts) != 5:
        await message.answer(
            "Foydalanish: /sell <miqdor> <valyuta> <narx> <narx_valyutasi>\n"
            "Masalan: /sell 100 coin 5000 dollar"
        )
        return

    if not parts[1].isdigit() or not parts[3].isdigit():
        await message.answer("Miqdor va narx butun son bo'lishi kerak.")
        return

    sell_amount, price_amount = int(parts[1]), int(parts[3])
    sell_currency, price_currency = parse_currency(parts[2]), parse_currency(parts[4])

    if not sell_currency or not price_currency:
        await message.answer("Valyuta noto'g'ri. Mavjud: dollar, diamond (olmos), coin")
        return
    if sell_currency == price_currency:
        await message.answer("Ikki xil valyuta tanlang.")
        return
    if sell_amount <= 0 or price_amount <= 0:
        await message.answer("Miqdor musbat bo'lishi kerak.")
        return

    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    user_row = await db.get_user(message.from_user.id)
    sell_col = CURRENCY_COLUMN[sell_currency]
    if user_row[sell_col] < sell_amount:
        await message.answer(f"Balansingizda yetarli {CURRENCY_EMOJI[sell_currency]} yo'q.")
        return

    # Escrow: hold the offered amount out of the seller's balance until sold or cancelled.
    await db.add_balance(message.from_user.id, **{sell_col: -sell_amount})
    listing_id = await db.create_listing(message.from_user.id, sell_currency, sell_amount, price_currency, price_amount)

    await message.answer(
        f"✅ E'lon joylandi (#{listing_id}): {sell_amount}{CURRENCY_EMOJI[sell_currency]} → "
        f"{price_amount}{CURRENCY_EMOJI[price_currency]}\n"
        f"Bekor qilish uchun: /cancel {listing_id}"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    if message.from_user.id not in SELLER_IDS:
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /cancel <e'lon raqami>")
        return

    listing_id = int(parts[1])
    listing = await db.get_listing(listing_id)
    if not listing or listing["seller_id"] != message.from_user.id:
        await message.answer("Bu e'lon sizga tegishli emas.")
        return

    ok = await db.transition_listing(listing_id, "cancelled")
    if not ok:
        await message.answer("Bu e'lon allaqachon yopilgan.")
        return

    sell_col = CURRENCY_COLUMN[listing["sell_currency"]]
    await db.add_balance(message.from_user.id, **{sell_col: listing["sell_amount"]})
    await message.answer(
        f"❌ E'lon #{listing_id} bekor qilindi, {listing['sell_amount']}{CURRENCY_EMOJI[listing['sell_currency']]} qaytarildi."
    )


@router.message(Command("mylistings"))
async def cmd_mylistings(message: Message) -> None:
    if message.from_user.id not in SELLER_IDS:
        return

    listings = await db.seller_listings(message.from_user.id)
    if not listings:
        await message.answer("Sizda faol e'lonlar yo'q.")
        return

    lines = ["<b>Sizning faol e'lonlaringiz:</b>", ""] + [listing_line(l) for l in listings]
    await message.answer("\n".join(lines))


async def build_market_view() -> tuple[str, InlineKeyboardMarkup | None]:
    listings = await db.active_listings()
    if not listings:
        return "Bozorda hozircha hech narsa yo'q.", None

    lines = ["🛒 <b>BOZOR</b>", ""] + [listing_line(l) for l in listings]
    buttons = [
        [InlineKeyboardButton(text=f"🛒 #{l['listing_id']} sotib olish", callback_data=f"market:buy:{l['listing_id']}")]
        for l in listings
    ]
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("market"))
async def cmd_market(message: Message) -> None:
    text, kb = await build_market_view()
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("market:buy:"))
async def on_market_buy(callback: CallbackQuery, bot: Bot) -> None:
    listing_id = int(callback.data.split(":")[2])
    listing = await db.get_listing(listing_id)
    if not listing or listing["status"] != "active":
        await callback.answer("Bu e'lon endi mavjud emas.", show_alert=True)
        return
    if listing["seller_id"] == callback.from_user.id:
        await callback.answer("O'z e'loningizni sotib ololmaysiz.", show_alert=True)
        return

    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    buyer_row = await db.get_user(callback.from_user.id)
    price_col = CURRENCY_COLUMN[listing["price_currency"]]
    if buyer_row[price_col] < listing["price_amount"]:
        await callback.answer(f"Balansingizda yetarli {CURRENCY_EMOJI[listing['price_currency']]} yo'q.", show_alert=True)
        return

    claimed = await db.transition_listing(listing_id, "sold")
    if not claimed:
        await callback.answer("Bu e'lonni boshqa birov sotib oldi.", show_alert=True)
        return

    sell_col = CURRENCY_COLUMN[listing["sell_currency"]]
    await db.add_balance(
        callback.from_user.id,
        **{price_col: -listing["price_amount"], sell_col: listing["sell_amount"]},
    )
    await db.add_balance(listing["seller_id"], **{price_col: listing["price_amount"]})

    await callback.answer("Xarid muvaffaqiyatli! ✅")
    try:
        await callback.message.edit_text(callback.message.text + f"\n\n✅ #{listing_id} sotildi.")
    except TelegramBadRequest:
        pass

    try:
        await bot.send_message(
            listing["seller_id"],
            f"💰 E'loningiz #{listing_id} sotildi: {listing['sell_amount']}{CURRENCY_EMOJI[listing['sell_currency']]} "
            f"→ {listing['price_amount']}{CURRENCY_EMOJI[listing['price_currency']]} hisobingizga qo'shildi.",
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
