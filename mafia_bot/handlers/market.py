from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import texts
from config import SELLER_IDS
from economy import CURRENCY_COLUMN, CURRENCY_EMOJI, parse_currency
from i18n import texts_for_user

router = Router(name="market")


def _amount(value: int, currency: str) -> str:
    return f"{value}{CURRENCY_EMOJI[currency]}"


def listing_line(listing) -> str:
    return (
        f"#{listing['listing_id']}: {_amount(listing['sell_amount'], listing['sell_currency'])} "
        f"→ {_amount(listing['price_amount'], listing['price_currency'])}"
    )


@router.message(Command("sell"))
async def cmd_sell(message: Message, L=texts) -> None:
    if message.from_user.id not in SELLER_IDS:
        return

    parts = message.text.split()
    if len(parts) != 5:
        await message.answer(L.MARKET_SELL_USAGE)
        return

    if not parts[1].isdigit() or not parts[3].isdigit():
        await message.answer(L.MARKET_NOT_NUMBER)
        return

    sell_amount, price_amount = int(parts[1]), int(parts[3])
    sell_currency, price_currency = parse_currency(parts[2]), parse_currency(parts[4])

    if not sell_currency or not price_currency:
        await message.answer(L.MARKET_BAD_CURRENCY)
        return
    if sell_currency == price_currency:
        await message.answer(L.MARKET_SAME_CURRENCY)
        return
    if sell_amount <= 0 or price_amount <= 0:
        await message.answer(L.MARKET_NOT_POSITIVE)
        return

    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    sell_col = CURRENCY_COLUMN[sell_currency]
    # Escrow: hold the offered amount out of the seller's balance until sold or cancelled.
    if not await db.spend_balance(message.from_user.id, sell_col, sell_amount):
        await message.answer(L.NOT_ENOUGH_BALANCE.format(emoji=CURRENCY_EMOJI[sell_currency]))
        return
    listing_id = await db.create_listing(message.from_user.id, sell_currency, sell_amount, price_currency, price_amount)

    await message.answer(
        L.MARKET_LISTED.format(
            id=listing_id, sell=_amount(sell_amount, sell_currency), price=_amount(price_amount, price_currency)
        )
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, L=texts) -> None:
    if message.from_user.id not in SELLER_IDS:
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(L.MARKET_CANCEL_USAGE)
        return

    listing_id = int(parts[1])
    listing = await db.get_listing(listing_id)
    if not listing or listing["seller_id"] != message.from_user.id:
        await message.answer(L.MARKET_NOT_YOURS)
        return

    ok = await db.transition_listing(listing_id, "cancelled")
    if not ok:
        await message.answer(L.MARKET_ALREADY_CLOSED)
        return

    sell_col = CURRENCY_COLUMN[listing["sell_currency"]]
    await db.add_balance(message.from_user.id, **{sell_col: listing["sell_amount"]})
    await message.answer(
        L.MARKET_CANCELLED.format(id=listing_id, amount=_amount(listing["sell_amount"], listing["sell_currency"]))
    )


@router.message(Command("mylistings"))
async def cmd_mylistings(message: Message, L=texts) -> None:
    if message.from_user.id not in SELLER_IDS:
        return

    listings = await db.seller_listings(message.from_user.id)
    if not listings:
        await message.answer(L.MARKET_NO_LISTINGS_MINE)
        return

    lines = [L.MARKET_MY_LISTINGS, ""] + [listing_line(l) for l in listings]
    await message.answer("\n".join(lines))


async def build_market_view(L=texts) -> tuple[str, InlineKeyboardMarkup | None]:
    listings = await db.active_listings()
    if not listings:
        return L.MARKET_EMPTY, None

    lines = [L.MARKET_TITLE, ""] + [listing_line(l) for l in listings]
    buttons = [
        [
            InlineKeyboardButton(
                text=L.MARKET_BUY_BUTTON.format(id=l["listing_id"]), callback_data=f"market:buy:{l['listing_id']}"
            )
        ]
        for l in listings
    ]
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("market"))
async def cmd_market(message: Message, L=texts) -> None:
    text, kb = await build_market_view(L)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("market:buy:"))
async def on_market_buy(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    raw = callback.data.split(":")[2]
    listing = await db.get_listing(int(raw)) if raw.isdigit() else None
    listing_id = listing["listing_id"] if listing else None
    if not listing or listing["status"] != "active":
        await callback.answer(UL.MARKET_GONE, show_alert=True)
        return
    if listing["seller_id"] == callback.from_user.id:
        await callback.answer(UL.MARKET_OWN, show_alert=True)
        return

    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    price_col = CURRENCY_COLUMN[listing["price_currency"]]
    if not await db.spend_balance(callback.from_user.id, price_col, listing["price_amount"]):
        await callback.answer(
            UL.NOT_ENOUGH_BALANCE.format(emoji=CURRENCY_EMOJI[listing["price_currency"]]), show_alert=True
        )
        return

    claimed = await db.transition_listing(listing_id, "sold")
    if not claimed:
        # Boshqa xaridor oldinroq ulgurdi — to'langan summa qaytariladi.
        await db.add_balance(callback.from_user.id, **{price_col: listing["price_amount"]})
        await callback.answer(UL.MARKET_SOLD_TO_OTHER, show_alert=True)
        return

    sell_col = CURRENCY_COLUMN[listing["sell_currency"]]
    await db.add_balance(callback.from_user.id, **{sell_col: listing["sell_amount"]})
    await db.add_balance(listing["seller_id"], **{price_col: listing["price_amount"]})

    await callback.answer(UL.MARKET_BOUGHT)
    try:
        await callback.message.edit_text(callback.message.text + "\n\n" + UL.MARKET_SOLD_MARK.format(id=listing_id))
    except TelegramBadRequest:
        pass

    seller_texts = await texts_for_user(listing["seller_id"])
    try:
        await bot.send_message(
            listing["seller_id"],
            seller_texts.MARKET_SOLD_NOTICE.format(
                id=listing_id,
                sell=_amount(listing["sell_amount"], listing["sell_currency"]),
                price=_amount(listing["price_amount"], listing["price_currency"]),
            ),
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
