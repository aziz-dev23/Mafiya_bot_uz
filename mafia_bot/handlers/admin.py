from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from config import ADMIN_IDS
from economy import ITEMS

router = Router(name="admin")


async def build_profile_view(
    user_id: int, full_name: str, username: str | None = None
) -> tuple[str, InlineKeyboardMarkup]:
    await db.ensure_user(user_id, full_name, username)
    user_row = await db.get_user(user_id)
    points = await db.points_summary(user_id)
    hero_level = await db.get_hero_level(user_id)
    hero_line = f"{hero_level}-daraja" if hero_level else "yo'q (/geroy)"
    inventory_rows = await db.get_inventory(user_id)
    inventory_by_key = {row["item_key"]: row for row in inventory_rows}

    lines = [
        f"👤 <b>{full_name}</b>",
        f"🆔 ID: <code>{user_id}</code>",
        "",
        f"💵 Dollar: {user_row['dollars']}",
        f"💎 Olmos: {user_row['diamonds']}",
        f"🪙 Coin: {user_row['coins']}",
        "",
        f"🏅 Ball — kunlik: {points['daily']} | haftalik: {points['weekly']} | "
        f"oylik: {points['monthly']} | jami: {points['total']}",
        "",
        f"🦸 Geroy: {hero_line}",
        "",
        "🎒 <b>Buyumlar:</b>",
    ]
    for key, item in ITEMS.items():
        row = inventory_by_key.get(key)
        count = row["count"] if row else 0
        lines.append(f"{item['emoji']} {item['name']}: {count} ta")

    lines.append("")
    lines.append(f"🎮 O'yinlar: {user_row['games']} | 🏆 G'alabalar: {user_row['wins']}")
    if inventory_rows:
        lines.append("")
        lines.append("⚙️ Buyumlarni yoqish/o'chirish uchun pastdagi tugmalarni bosing:")

    buttons = []
    if inventory_rows:
        for row in inventory_rows:
            item = ITEMS.get(row["item_key"])
            if not item:
                continue
            state = "🟢 ON" if row["enabled"] else "🔴 OFF"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{item['emoji']} {item['name']} · {state}",
                        callback_data=f"toggleitem_profile:{row['item_key']}",
                    )
                ]
            )
    buttons.append([InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:back")])

    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    text, kb = await build_profile_view(
        message.from_user.id, message.from_user.full_name, message.from_user.username
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("toggleitem_profile:"))
async def on_toggle_item_profile(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    rows = await db.get_inventory(callback.from_user.id)
    row = next((r for r in rows if r["item_key"] == key), None)
    if not row:
        await callback.answer("Bu buyum sizda yo'q.", show_alert=True)
        return

    new_state = not bool(row["enabled"])
    await db.set_item_enabled(callback.from_user.id, key, new_state)
    await callback.answer("Yoqildi ✅" if new_state else "O'chirildi")

    text, kb = await build_profile_view(
        callback.from_user.id, callback.from_user.full_name, callback.from_user.username
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass


def _parse_target_and_amount(message: Message) -> tuple[int | None, int | None, str | None]:
    parts = message.text.split()
    if message.reply_to_message:
        if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
            return None, None, "Foydalanish: xabarga reply qiling va miqdorni yozing, masalan /addcash 1000"
        return message.reply_to_message.from_user.id, int(parts[1]), None

    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].lstrip("-").isdigit():
        return None, None, "Foydalanish: /addcash <user_id> <miqdor> yoki xabarga reply qilib /addcash <miqdor>"
    return int(parts[1]), int(parts[2]), None


@router.message(Command("addcash"))
async def cmd_addcash(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, dollars=amount)
    await message.answer(f"✅ {amount}💵 balansga qo'shildi (user_id={user_id}).")


@router.message(Command("addgem"))
async def cmd_addgem(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, diamonds=amount)
    await message.answer(f"✅ {amount}💎 balansga qo'shildi (user_id={user_id}).")


@router.message(Command("addcoin"))
async def cmd_addcoin(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, coins=amount)
    await message.answer(f"✅ {amount}🪙 balansga qo'shildi (user_id={user_id}).")
