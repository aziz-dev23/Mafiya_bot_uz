from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import texts
from config import ADMIN_IDS
from game.models import Role
from economy import ITEMS
from utils import esc

router = Router(name="admin")


async def build_profile_view(
    user_id: int, full_name: str, username: str | None = None, L=texts
) -> tuple[str, InlineKeyboardMarkup]:
    await db.ensure_user(user_id, full_name, username)
    user_row = await db.get_user(user_id)
    points = await db.points_summary(user_id)
    hero_level = await db.get_hero_level(user_id)
    inventory_rows = await db.get_inventory(user_id)
    inventory_by_key = {row["item_key"]: row for row in inventory_rows}

    lines = [
        L.PROFILE_TEXT.format(
            name=esc(full_name), user_id=user_id,
            dollars=user_row["dollars"], diamonds=user_row["diamonds"], coins=user_row["coins"],
            daily=points["daily"], weekly=points["weekly"], monthly=points["monthly"], total=points["total"],
            hero=L.PROFILE_HERO_LEVEL.format(level=hero_level) if hero_level else L.PROFILE_HERO_NONE,
        )
    ]
    for key, item in ITEMS.items():
        row = inventory_by_key.get(key)
        lines.append(L.PROFILE_ITEM_LINE.format(emoji=item["emoji"], name=L.ITEM_NAMES[key], count=row["count"] if row else 0))

    lines.append("")
    lines.append(L.PROFILE_GAMES.format(games=user_row["games"], wins=user_row["wins"]))
    role_stats = await db.get_role_stats(user_id)
    if role_stats:
        lines.append("")
        lines.append(L.PROFILE_ROLE_STATS_HEADER)
        for row in role_stats:
            if row["role"] not in Role._value2member_map_:
                continue
            pct = round(100 * row["wins"] / row["games"]) if row["games"] else 0
            lines.append(
                L.PROFILE_ROLE_STATS_LINE.format(role=L.ROLE_NAMES[Role(row["role"])], games=row["games"], pct=pct)
            )
    if inventory_rows:
        lines.append("")
        lines.append(L.PROFILE_TOGGLE_HINT)

    buttons = []
    for row in inventory_rows:
        item = ITEMS.get(row["item_key"])
        if not item:
            continue
        state = L.PROFILE_ITEM_ON if row["enabled"] else L.PROFILE_ITEM_OFF
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{item['emoji']} {L.ITEM_NAMES[row['item_key']]} · {state}",
                    callback_data=f"toggleitem_profile:{row['item_key']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text=L.MAIN_MENU_BUTTON, callback_data="menu:back")])

    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("profile"))
async def cmd_profile(message: Message, L=texts) -> None:
    text, kb = await build_profile_view(
        message.from_user.id, message.from_user.full_name, message.from_user.username, L
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("toggleitem_profile:"))
async def on_toggle_item_profile(callback: CallbackQuery, UL=texts) -> None:
    key = callback.data.split(":", 1)[1]
    rows = await db.get_inventory(callback.from_user.id)
    row = next((r for r in rows if r["item_key"] == key), None)
    if not row:
        await callback.answer(UL.ITEM_NOT_OWNED, show_alert=True)
        return

    new_state = not bool(row["enabled"])
    await db.set_item_enabled(callback.from_user.id, key, new_state)
    await callback.answer(UL.ITEM_ENABLED if new_state else UL.ITEM_DISABLED)

    text, kb = await build_profile_view(
        callback.from_user.id, callback.from_user.full_name, callback.from_user.username, UL
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass


def _parse_target_and_amount(message: Message, L=texts) -> tuple[int | None, int | None, str | None]:
    parts = message.text.split()
    if message.reply_to_message:
        if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
            return None, None, L.ADMIN_REPLY_USAGE
        return message.reply_to_message.from_user.id, int(parts[1]), None

    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].lstrip("-").isdigit():
        return None, None, L.ADMIN_USAGE
    return int(parts[1]), int(parts[2]), None


@router.message(Command("addcash"))
async def cmd_addcash(message: Message, L=texts) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message, L)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, dollars=amount)
    await message.answer(L.ADMIN_BALANCE_ADDED.format(amount=amount, emoji="💵", user_id=user_id))


@router.message(Command("addgem"))
async def cmd_addgem(message: Message, L=texts) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message, L)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, diamonds=amount)
    await message.answer(L.ADMIN_BALANCE_ADDED.format(amount=amount, emoji="💎", user_id=user_id))


@router.message(Command("addcoin"))
async def cmd_addcoin(message: Message, L=texts) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message, L)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, coins=amount)
    await message.answer(L.ADMIN_BALANCE_ADDED.format(amount=amount, emoji="🪙", user_id=user_id))
