from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from economy import CURRENCY_COLUMN, CURRENCY_EMOJI, ITEMS

router = Router(name="items")


def _item_line(key: str) -> str:
    item = ITEMS[key]
    return f"{item['emoji']} {item['name']} — {item['price']}{CURRENCY_EMOJI[item['currency']]}"


def build_store_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=_item_line(key), callback_data=f"buyitem:{key}")] for key in ITEMS]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("dokon", "items"))
async def cmd_store(message: Message) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(
        "🎒 <b>BUYUMLAR DO'KONI</b>\n"
        "O'yin ichida foydali bo'ladigan buyumlarni sotib oling. "
        "Sotib olingan buyum avtomatik yoniq (YONIQ) holatda bo'ladi — "
        "/sumka orqali o'chirib qo'yishingiz mumkin.\n\n"
        "Kerakli buyumni tanlang:",
        reply_markup=build_store_keyboard(),
    )


@router.callback_query(F.data.startswith("buyitem:"))
async def on_buy_item(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    item = ITEMS.get(key)
    if not item:
        await callback.answer("Bu buyum topilmadi.", show_alert=True)
        return

    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    user_row = await db.get_user(callback.from_user.id)
    col = CURRENCY_COLUMN[item["currency"]]
    if user_row[col] < item["price"]:
        await callback.answer(f"Balansingizda yetarli {CURRENCY_EMOJI[item['currency']]} yo'q.", show_alert=True)
        return

    await db.add_balance(callback.from_user.id, **{col: -item["price"]})
    await db.add_item(callback.from_user.id, key, 1)

    await callback.answer(f"✅ {item['emoji']} {item['name']} sotib olindi!")
    try:
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ Xarid qilindi: {item['emoji']} {item['name']}"
        )
    except TelegramBadRequest:
        pass


def build_inventory_text_and_keyboard(rows) -> tuple[str, InlineKeyboardMarkup]:
    if not rows:
        return (
            "🎒 Sizda hali hech qanday buyum yo'q.\n\n/dokon orqali sotib olishingiz mumkin.",
            InlineKeyboardMarkup(inline_keyboard=[]),
        )

    lines = ["🎒 <b>MENING BUYUMLARIM</b>", ""]
    buttons = []
    for row in rows:
        item = ITEMS.get(row["item_key"])
        if not item:
            continue
        state = "🟢 YONIQ" if row["enabled"] else "🔴 O'CHIQ"
        lines.append(f"{item['emoji']} {item['name']}: {row['count']} ta — {state}")
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{item['emoji']} {item['name']}: {'O`chirish' if row['enabled'] else 'Yoqish'}",
                    callback_data=f"toggleitem:{row['item_key']}",
                )
            ]
        )
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("sumka", "inventory"))
async def cmd_inventory(message: Message) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    rows = await db.get_inventory(message.from_user.id)
    text, kb = build_inventory_text_and_keyboard(rows)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("toggleitem:"))
async def on_toggle_item(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    rows = await db.get_inventory(callback.from_user.id)
    row = next((r for r in rows if r["item_key"] == key), None)
    if not row:
        await callback.answer("Bu buyum sizda yo'q.", show_alert=True)
        return

    new_state = not bool(row["enabled"])
    await db.set_item_enabled(callback.from_user.id, key, new_state)
    await callback.answer("Yoqildi ✅" if new_state else "O'chirildi")

    rows = await db.get_inventory(callback.from_user.id)
    text, kb = build_inventory_text_and_keyboard(rows)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
