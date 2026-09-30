"""🏰 /premium — guruh premiumi (Stars obunasi, guruh admini to'laydi) va 🏆 /turnir (faqat premium guruhda)."""
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message

import cosmetics
import db
import group_features
import purchases
import texts
from config import TIMEZONE_OFFSET_HOURS
from economy import (
    GROUP_PREMIUM_PRICE_STARS,
    GROUP_TITLE_GAMES,
    STARS_CURRENCY,
    TOURNAMENT_GAME_OPTIONS,
    TOURNAMENT_MIN_PLAYERS,
    TOURNAMENT_MIN_PRIZE,
    TOURNAMENT_MVP_TOP,
    TOURNAMENT_POINTS_ALIVE,
    TOURNAMENT_POINTS_MVP,
    TOURNAMENT_POINTS_WIN,
    TOURNAMENT_PRIZE_OPTIONS,
    TOURNAMENT_PRIZE_SPLIT,
    TOURNAMENT_TIMEOUT_HOURS,
    VIP_PERIOD_SECONDS,
)

router = Router(name="group_premium")
_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))
GROUP_TYPES = ("group", "supergroup")


def _date(ts: int) -> str:
    return datetime.fromtimestamp(ts, _TZ).strftime("%d.%m.%Y")


async def premium_view(chat_id: int, L=texts) -> tuple[str, InlineKeyboardMarkup | None]:
    title = await cosmetics.group_title_text(chat_id)
    perks = L.GROUP_PREMIUM_PERKS.format(games=GROUP_TITLE_GAMES, name=title.removeprefix("🏰 "))
    until = await db.group_premium_until(chat_id)
    if await db.is_group_premium(chat_id):
        return L.GROUP_PREMIUM_ACTIVE.format(date=_date(until), perks=perks), None
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text=L.GROUP_PREMIUM_BUTTON.format(price=GROUP_PREMIUM_PRICE_STARS), callback_data="gp:buy"
    )]])
    return L.GROUP_PREMIUM_INACTIVE.format(price=GROUP_PREMIUM_PRICE_STARS, perks=perks), kb


@router.message(Command("premium"))
async def cmd_premium(message: Message, L=texts, UL=texts) -> None:
    if message.chat.type not in GROUP_TYPES:
        await message.answer(UL.GROUP_ONLY)
        return
    text, kb = await premium_view(message.chat.id, L)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "gp:buy")
async def on_premium_buy(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    chat = callback.message.chat
    if not await purchases.is_chat_admin(bot, chat.id, callback.from_user.id):
        await callback.answer(UL.ADMIN_ONLY, show_alert=True)
        return
    title = chat.title or str(chat.id)
    await db.set_group_title(chat.id, title)
    try:
        # Obuna faqat createInvoiceLink orqali; havola shaxsiy chatga — boshqa odam to'lab yubormasligi uchun.
        link = await bot.create_invoice_link(
            title=UL.GROUP_PREMIUM_INVOICE_TITLE,
            description=UL.GROUP_PREMIUM_INVOICE_DESCRIPTION.format(chat=title),
            payload=purchases.group_premium_payload(chat.id, callback.from_user.id),
            currency=STARS_CURRENCY,
            prices=[LabeledPrice(label=UL.GROUP_PREMIUM_INVOICE_TITLE, amount=GROUP_PREMIUM_PRICE_STARS)],
            subscription_period=VIP_PERIOD_SECONDS,
            provider_token="",
        )
        text, _ = await premium_view(chat.id, UL)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text=UL.GROUP_PREMIUM_BUTTON.format(price=GROUP_PREMIUM_PRICE_STARS), url=link
        )]])
        await bot.send_message(callback.from_user.id, text, reply_markup=kb)
    except TelegramAPIError:
        me = await bot.get_me()
        await callback.answer(UL.START_BOT_PRIVATE.format(bot=me.username), show_alert=True)
        return
    await callback.answer(UL.GROUP_PREMIUM_LINK_SENT, show_alert=True)


# ---------- 🏆 Turnir ----------


async def _check_admin_premium(bot: Bot, chat_id: int, user_id: int, UL) -> str | None:
    """Xato matni yoki None."""
    if not await purchases.is_chat_admin(bot, chat_id, user_id):
        return UL.ADMIN_ONLY
    if not await db.is_group_premium(chat_id):
        return UL.GROUP_PREMIUM_REQUIRED
    return None


def games_keyboard(L=texts) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=L.TOURNAMENT_GAMES_BUTTON.format(n=n), callback_data=f"trn:g:{n}")
        for n in TOURNAMENT_GAME_OPTIONS
    ]])


def prize_keyboard(games: int, L=texts) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=L.TOURNAMENT_PRIZE_BUTTON.format(prize=p), callback_data=f"trn:p:{games}:{p}")
        for p in TOURNAMENT_PRIZE_OPTIONS if p >= TOURNAMENT_MIN_PRIZE
    ]])


def started_text(games: int, prize: int, L=texts) -> str:
    p1, p2, p3 = TOURNAMENT_PRIZE_SPLIT
    return L.TOURNAMENT_STARTED.format(
        games=games, min_players=TOURNAMENT_MIN_PLAYERS, prize=prize, p1=p1, p2=p2, p3=p3,
        win=TOURNAMENT_POINTS_WIN, alive=TOURNAMENT_POINTS_ALIVE, mvp_top=TOURNAMENT_MVP_TOP,
        mvp=TOURNAMENT_POINTS_MVP, hours=TOURNAMENT_TIMEOUT_HOURS,
    )


async def status_view(t, L=texts) -> tuple[str, InlineKeyboardMarkup | None]:
    rows = await db.tournament_scores(t["tournament_id"])
    table = group_features.table_text(rows, t["games_played"], t["games_total"], L)
    text = L.TOURNAMENT_STATUS.format(played=t["games_played"], games=t["games_total"], prize=t["prize"], table=table)
    kb = None
    if t["games_played"] == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text=L.TOURNAMENT_CANCEL_BUTTON, callback_data=f"trn:cancel:{t['tournament_id']}"
        )]])
    return text, kb


@router.message(Command("turnir", "tournament"))
async def cmd_tournament(message: Message, bot: Bot, L=texts, UL=texts) -> None:
    if message.chat.type not in GROUP_TYPES:
        await message.answer(UL.GROUP_ONLY)
        return
    error = await _check_admin_premium(bot, message.chat.id, message.from_user.id, UL)
    if error:
        await message.answer(error)
        return
    t = await db.active_tournament(message.chat.id)
    if t:
        text, kb = await status_view(t, L)
        await message.answer(text, reply_markup=kb)
        return
    await message.answer(L.TOURNAMENT_CHOOSE_GAMES.format(min_players=TOURNAMENT_MIN_PLAYERS), reply_markup=games_keyboard(L))


async def _edit(callback: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None = None) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("trn:"))
async def on_tournament(callback: CallbackQuery, bot: Bot, L=texts, UL=texts) -> None:
    chat_id = callback.message.chat.id
    error = await _check_admin_premium(bot, chat_id, callback.from_user.id, UL)
    if error:
        await callback.answer(error, show_alert=True)
        return
    parts = callback.data.split(":")[1:]
    if parts[0] == "g" and len(parts) == 2 and parts[1].isdigit() and int(parts[1]) in TOURNAMENT_GAME_OPTIONS:
        await callback.answer()
        await _edit(callback, L.TOURNAMENT_CHOOSE_PRIZE.format(games=parts[1]), prize_keyboard(int(parts[1]), L))
        return
    if parts[0] == "p" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        games, prize = int(parts[1]), int(parts[2])
        if games not in TOURNAMENT_GAME_OPTIONS or prize not in TOURNAMENT_PRIZE_OPTIONS or prize < TOURNAMENT_MIN_PRIZE:
            await callback.answer()
            return
        if await db.active_tournament(chat_id):
            await callback.answer(UL.TOURNAMENT_ALREADY, show_alert=True)
            return
        await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
        if await db.create_tournament(chat_id, callback.from_user.id, games, prize) is None:
            await callback.answer(UL.TOURNAMENT_NOT_ENOUGH.format(prize=prize), show_alert=True)
            return
        await callback.answer()
        await _edit(callback, started_text(games, prize, L))
        return
    if parts[0] == "cancel":
        t = await db.active_tournament(chat_id)
        if not t or str(t["tournament_id"]) != parts[-1] or not await group_features.cancel_tournament(t):
            await callback.answer(UL.TOURNAMENT_CANNOT_CANCEL, show_alert=True)
            return
        await callback.answer()
        await _edit(callback, L.TOURNAMENT_CANCELLED.format(prize=t["prize"]))
        return
    await callback.answer()
