import time
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import audit
import cosmetics
import db
import texts
from config import ADMIN_IDS, TIMEZONE_OFFSET_HOURS
from game.models import Role
from economy import FRAME, ITEMS, TITLE, VIP_HISTORY_GAMES
from utils import esc

router = Router(name="admin")
_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))


async def build_profile_view(
    user_id: int, full_name: str, username: str | None = None, L=texts
) -> tuple[str, InlineKeyboardMarkup]:
    await db.ensure_user(user_id, full_name, username)
    user_row = await db.get_user(user_id)
    points = await db.points_summary(user_id)
    hero_level = await db.get_hero_level(user_id)
    inventory_rows = await db.get_inventory(user_id)
    inventory_by_key = {row["item_key"]: row for row in inventory_rows}
    active = await cosmetics.active(user_id)

    lines = [
        L.PROFILE_TEXT.format(
            name=cosmetics.display_name(esc(full_name), L, active.get(TITLE), hero_level, await db.is_vip(user_id)),
            user_id=user_id,
            dollars=user_row["dollars"], diamonds=user_row["diamonds"], coins=user_row["coins"],
            daily=points["daily"], weekly=points["weekly"], monthly=points["monthly"], total=points["total"],
            hero=L.PROFILE_HERO_LEVEL.format(level=hero_level) if hero_level else L.PROFILE_HERO_NONE,
        )
    ]
    for key, item in ITEMS.items():
        row = inventory_by_key.get(key)
        count = row["count"] if row else 0
        if key == "rifle":
            lines.append(L.INVENTORY_RIFLE_LINE.format(count=count))
            continue
        state = (L.PROFILE_ITEM_ON if row["enabled"] else L.PROFILE_ITEM_OFF) + " " if row and count else ""
        lines.append(state + L.PROFILE_ITEM_LINE.format(emoji=item["emoji"], name=L.ITEM_NAMES[key], count=count))

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
    vip_until = await db.vip_until(user_id)
    if vip_until > time.time():
        lines.append("")
        lines.append(L.PROFILE_VIP_LINE.format(date=_date(vip_until)))
        lines.append(await _history_block(user_id, L))
    if inventory_rows:
        lines.append("")
        lines.append(L.PROFILE_TOGGLE_HINT)

    buttons = []
    for row in inventory_rows:
        item = ITEMS.get(row["item_key"])
        if not item or row["item_key"] == "rifle":  # Miltiq tunda qo'lda ishlatiladi
            continue
        state = L.PROFILE_ITEM_ON if row["enabled"] else L.PROFILE_ITEM_OFF
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{state} {item['emoji']} {L.ITEM_NAMES[row['item_key']]}",
                    callback_data=f"toggleitem_profile:{row['item_key']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text=L.MAIN_MENU_BUTTON, callback_data="menu:back")])

    return _framed("\n".join(lines), active.get(FRAME), L), InlineKeyboardMarkup(inline_keyboard=buttons)


def _date(ts: int) -> str:
    return datetime.fromtimestamp(ts, _TZ).strftime("%d.%m.%Y")


async def _history_block(user_id: int, L) -> str:
    """👑 VIP: oxirgi VIP_HISTORY_GAMES ta o'yin (rol va natija)."""
    rows = await db.recent_games(user_id, VIP_HISTORY_GAMES)
    if not rows:
        return L.PROFILE_HISTORY_EMPTY
    lines = [L.PROFILE_HISTORY_HEADER]
    for row in rows:
        role = L.ROLE_NAMES[Role(row["role"])] if row["role"] in Role._value2member_map_ else row["role"]
        result = L.PROFILE_HISTORY_AFK if row["afk"] else (L.PROFILE_HISTORY_WIN if row["won"] else L.PROFILE_HISTORY_LOSS)
        lines.append(L.PROFILE_HISTORY_LINE.format(date=_date(row["ended_at"]), role=role, result=result))
    return "\n".join(lines)


def _framed(text: str, frame_key: str | None, L) -> str:
    """Profil ramkasi: matnning tepasi va pastidagi bezak qator."""
    line = cosmetics.frame_line(frame_key, L)
    return f"{line}\n{text}\n{line}" if line else text


async def build_public_profile(user_id: int, L=texts) -> str:
    """Ochiq profil (reply orqali): unvon, ramka, 🦸, o'yinlar, g'alabalar, /top o'rni. Balans va buyumlar yo'q."""
    user_row = await db.get_user(user_id)
    if not user_row:
        return L.PUBLIC_PROFILE_UNKNOWN
    active = await cosmetics.active(user_id)
    rank = await db.points_rank(user_id)
    text = L.PUBLIC_PROFILE.format(
        name=cosmetics.display_name(
            esc(user_row["full_name"]), L, active.get(TITLE), await db.get_hero_level(user_id),
            await db.is_vip(user_id),
        ),
        games=user_row["games"], wins=user_row["wins"],
        place=rank[0] if rank else L.PUBLIC_PROFILE_NO_RANK,
    )
    return _framed(text, active.get(FRAME), L)


@router.message(Command("profile"))
async def cmd_profile(message: Message, L=texts) -> None:
    replied = message.reply_to_message
    if replied and replied.from_user and not replied.from_user.is_bot and replied.from_user.id != message.from_user.id:
        await message.answer(await build_public_profile(replied.from_user.id, L))
        return
    text, kb = await build_profile_view(
        message.from_user.id, message.from_user.full_name, message.from_user.username, L
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("toggleitem_profile:"))
async def on_toggle_item_profile(callback: CallbackQuery, UL=texts) -> None:
    key = callback.data.split(":", 1)[1]
    rows = await db.get_inventory(callback.from_user.id)
    row = next((r for r in rows if r["item_key"] == key), None)
    if not row or key == "rifle":
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
async def cmd_addcash(message: Message, bot: Bot, L=texts) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message, L)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, dollars=amount)
    await message.answer(L.ADMIN_BALANCE_ADDED.format(amount=amount, emoji="💵", user_id=user_id))
    await audit.record(bot, message.from_user, "addcash", user_id, "dollar", amount)


@router.message(Command("addgem"))
async def cmd_addgem(message: Message, bot: Bot, L=texts) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message, L)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, diamonds=amount)
    await message.answer(L.ADMIN_BALANCE_ADDED.format(amount=amount, emoji="💎", user_id=user_id))
    await audit.record(bot, message.from_user, "addgem", user_id, "diamond", amount)


@router.message(Command("addcoin"))
async def cmd_addcoin(message: Message, bot: Bot, L=texts) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id, amount, error = _parse_target_and_amount(message, L)
    if error:
        await message.answer(error)
        return
    await db.ensure_user_exists(user_id)
    await db.add_balance(user_id, coins=amount)
    await message.answer(L.ADMIN_BALANCE_ADDED.format(amount=amount, emoji="🪙", user_id=user_id))
    await audit.record(bot, message.from_user, "addcoin", user_id, "coin", amount)
