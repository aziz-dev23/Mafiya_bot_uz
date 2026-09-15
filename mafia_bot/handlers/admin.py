from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import db
from config import ADMIN_IDS
from economy import ITEMS

router = Router(name="admin")


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    user_row = await db.get_user(message.from_user.id)
    clan_row = await db.get_user_clan(message.from_user.id)
    inventory_rows = await db.get_inventory(message.from_user.id)

    lines = [
        f"👤 <b>{message.from_user.full_name}</b>",
        f"🆔 ID: <code>{message.from_user.id}</code>",
        "",
        f"💵 Dollar: {user_row['dollars']}",
        f"💎 Olmos: {user_row['diamonds']}",
        f"🪙 Coin: {user_row['coins']}",
    ]
    if clan_row:
        lines.append(f"🏰 Klan: {clan_row['name']} [{clan_row['tag']}] ({user_row['clan_role']})")
    else:
        lines.append("🏰 Klan: yo'q")

    lines.append("")
    lines.append("🎒 <b>Buyumlar:</b>")
    if inventory_rows:
        for row in inventory_rows:
            item = ITEMS.get(row["item_key"])
            if not item:
                continue
            state = "🟢" if row["enabled"] else "🔴"
            lines.append(f"{item['emoji']} {item['name']}: {row['count']} ta {state}")
    else:
        lines.append("<i>(yo'q — /dokon orqali sotib oling)</i>")

    lines.append("")
    lines.append(f"🎮 O'yinlar: {user_row['games']} | 🏆 G'alabalar: {user_row['wins']}")
    await message.answer("\n".join(lines))


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
