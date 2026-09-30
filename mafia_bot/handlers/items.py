from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import texts
from economy import CURRENCY_COLUMN, CURRENCY_EMOJI, ITEMS

router = Router(name="items")

QUANTITY_OPTIONS = (1, 3, 5, 10)


def _price(key: str, qty: int = 1) -> str:
    item = ITEMS[key]
    return f"{item['price'] * qty}{CURRENCY_EMOJI[item['currency']]}"


def store_text(L=texts) -> str:
    return L.STORE_TEXT.format(rule=L.ITEM_STORE_RULE)


def build_store_keyboard(L=texts) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{ITEMS[key]['emoji']} {L.ITEM_NAMES[key]} — {_price(key)}", callback_data=f"buyitem:{key}"
            )
        ]
        for key in ITEMS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_quantity_keyboard(key: str, L=texts) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=L.QUANTITY_BUTTON.format(qty=qty), callback_data=f"buyitem_qty:{key}:{qty}")
        for qty in QUANTITY_OPTIONS
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[row, [InlineKeyboardButton(text=L.BACK_BUTTON, callback_data="buyitem_back")]]
    )


@router.message(Command("dokon", "items"))
async def cmd_store(message: Message, L=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(store_text(L), reply_markup=build_store_keyboard(L))


@router.callback_query(F.data.startswith("buyitem:"))
async def on_buy_item(callback: CallbackQuery, UL=texts) -> None:
    key = callback.data.split(":", 1)[1]
    item = ITEMS.get(key)
    if not item:
        await callback.answer(UL.ITEM_NOT_FOUND, show_alert=True)
        return

    await callback.answer()
    try:
        await callback.message.edit_text(
            UL.ITEM_PRICE_LINE.format(emoji=item["emoji"], name=UL.ITEM_NAMES[key], price=_price(key)) + "\n"
            f"<i>{UL.ITEM_DESCRIPTIONS.get(key, '')}</i>\n\n" + UL.ITEM_HOW_MANY,
            reply_markup=build_quantity_keyboard(key, UL),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "buyitem_back")
async def on_buy_item_back(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    try:
        await callback.message.edit_text(store_text(UL), reply_markup=build_store_keyboard(UL))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("buyitem_qty:"))
async def on_buy_item_qty(callback: CallbackQuery, UL=texts) -> None:
    parts = callback.data.split(":")
    item = ITEMS.get(parts[1]) if len(parts) == 3 else None
    # Faqat tugmalardagi miqdorlar qabul qilinadi — soxta (manfiy) miqdor yuborib bo'lmaydi.
    if not item or not parts[2].isdigit() or int(parts[2]) not in QUANTITY_OPTIONS:
        await callback.answer(UL.ITEM_NOT_FOUND, show_alert=True)
        return
    key, qty = parts[1], int(parts[2])

    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    col = CURRENCY_COLUMN[item["currency"]]
    if not await db.spend_balance(callback.from_user.id, col, item["price"] * qty):
        await callback.answer(UL.NOT_ENOUGH_BALANCE.format(emoji=CURRENCY_EMOJI[item["currency"]]), show_alert=True)
        return

    await db.add_item(callback.from_user.id, key, qty)

    name = UL.ITEM_NAMES[key]
    await callback.answer(UL.ITEM_BOUGHT_ALERT.format(qty=qty, emoji=item["emoji"], name=name))
    try:
        await callback.message.edit_text(
            UL.ITEM_BOUGHT.format(qty=qty, emoji=item["emoji"], name=name, price=_price(key, qty))
        )
    except TelegramBadRequest:
        pass


def build_inventory_text_and_keyboard(rows, L=texts) -> tuple[str, InlineKeyboardMarkup]:
    if not rows:
        return L.INVENTORY_EMPTY, InlineKeyboardMarkup(inline_keyboard=[])

    lines = [L.INVENTORY_TITLE, ""]
    buttons = []
    for row in rows:
        key = row["item_key"]
        item = ITEMS.get(key)
        if not item:
            continue
        state = L.ITEM_STATE_ON if row["enabled"] else L.ITEM_STATE_OFF
        lines.append(L.INVENTORY_LINE.format(emoji=item["emoji"], name=L.ITEM_NAMES[key], count=row["count"], state=state))
        action = L.ITEM_TURN_OFF if row["enabled"] else L.ITEM_TURN_ON
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{item['emoji']} {L.ITEM_NAMES[key]}: {action}", callback_data=f"toggleitem:{key}"
                )
            ]
        )
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("sumka", "inventory"))
async def cmd_inventory(message: Message, L=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    rows = await db.get_inventory(message.from_user.id)
    text, kb = build_inventory_text_and_keyboard(rows, L)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("toggleitem:"))
async def on_toggle_item(callback: CallbackQuery, UL=texts) -> None:
    key = callback.data.split(":", 1)[1]
    rows = await db.get_inventory(callback.from_user.id)
    row = next((r for r in rows if r["item_key"] == key), None)
    if not row:
        await callback.answer(UL.ITEM_NOT_OWNED, show_alert=True)
        return

    new_state = not bool(row["enabled"])
    await db.set_item_enabled(callback.from_user.id, key, new_state)
    await callback.answer(UL.ITEM_ENABLED if new_state else UL.ITEM_DISABLED)

    rows = await db.get_inventory(callback.from_user.id)
    text, kb = build_inventory_text_and_keyboard(rows, UL)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
