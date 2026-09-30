"""🎟 /mavsum — daraja, XP, keyingi mukofotlar, tugashiga qolgan kunlar, premium yo'lak."""
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import season
import texts
from economy import SEASON_PREMIUM_PRICE_DIAMONDS

router = Router(name="season")


async def build_view(user_id: int, L=texts) -> tuple[str, InlineKeyboardMarkup | None]:
    text, can_buy = await season.season_view(user_id, L)
    kb = None
    if can_buy:
        button = InlineKeyboardButton(
            text=L.SEASON_PREMIUM_BUTTON.format(price=SEASON_PREMIUM_PRICE_DIAMONDS), callback_data="season:buy"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return text, kb


@router.message(Command("mavsum", "season"))
async def cmd_season(message: Message, L=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    text, kb = await build_view(message.from_user.id, L)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "season:buy")
async def on_buy_premium(callback: CallbackQuery, UL=texts) -> None:
    user_id = callback.from_user.id
    await db.ensure_user(user_id, callback.from_user.full_name, callback.from_user.username)
    status, rewards = await season.buy_premium(user_id)
    if status == "no_season":
        await callback.answer(UL.SEASON_NOT_ACTIVE, show_alert=True)
        return
    if status == "already":
        await callback.answer(UL.SEASON_ALREADY_PREMIUM, show_alert=True)
        return
    if status == "no_funds":
        await callback.answer(UL.NOT_ENOUGH_DIAMONDS, show_alert=True)
        return
    await callback.answer(UL.SEASON_PREMIUM_BOUGHT, show_alert=True)
    text, kb = await build_view(user_id, UL)
    if rewards:
        text += "\n\n" + UL.SEASON_REWARDS_GOT.format(
            rewards=", ".join(season.reward_text(r, season.current_season(), UL) for r in rewards)
        )
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
