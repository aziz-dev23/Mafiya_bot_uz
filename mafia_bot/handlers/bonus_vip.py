"""🎁 /bonus — kunlik bonus; 👑 /vip — VIP obuna holati va Stars obuna havolasi."""
import time
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message

import bonus
import db
import texts
import vip
from economy import DAILY_BONUS_DAYS, STARS_CURRENCY, VIP_DAILY_BONUS_MULTIPLIER, VIP_PERIOD_SECONDS, VIP_PRICE_STARS

router = Router(name="bonus_vip")


async def bonus_text(user_id: int, L=texts) -> str:
    result = await bonus.claim(user_id)
    if not result["ok"]:
        return L.BONUS_ALREADY.format(day=result["day"])
    next_day = result["day"] + 1 if result["day"] < DAILY_BONUS_DAYS else 1
    next_dollars, next_diamonds = bonus.bonus_for_day(next_day)
    if result["vip"]:
        next_dollars *= VIP_DAILY_BONUS_MULTIPLIER
    next_reward = f"{next_dollars}💵" + (L.BONUS_EXTRA_DIAMONDS.format(diamonds=next_diamonds) if next_diamonds else "")
    return L.BONUS_CLAIMED.format(
        day=result["day"],
        dollars=result["dollars"],
        extra=L.BONUS_EXTRA_DIAMONDS.format(diamonds=result["diamonds"]) if result["diamonds"] else "",
        vip=L.BONUS_VIP_NOTE if result["vip"] else "",
        next_day=next_day,
        next_dollars=next_reward,
    )


@router.message(Command("bonus"))
async def cmd_bonus(message: Message, UL=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(await bonus_text(message.from_user.id, UL))


@router.callback_query(F.data == "menu:bonus")
async def on_menu_bonus(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    await callback.message.answer(await bonus_text(callback.from_user.id, UL))


async def vip_view(bot: Bot, user_id: int, L=texts) -> tuple[str, InlineKeyboardMarkup | None]:
    until = await db.vip_until(user_id)
    if until > time.time():
        date = datetime.fromtimestamp(until, bonus.TZ).strftime("%d.%m.%Y")
        return L.VIP_TEXT_ACTIVE.format(date=date, perks=L.VIP_PERKS), None
    text = L.VIP_TEXT_INACTIVE.format(price=VIP_PRICE_STARS, perks=L.VIP_PERKS)
    try:
        # Stars obunasi faqat createInvoiceLink orqali; Telegram har 30 kunda o'zi yangilaydi.
        link = await bot.create_invoice_link(
            title=L.VIP_INVOICE_TITLE,
            description=L.VIP_INVOICE_DESCRIPTION,
            payload=vip.build_payload(user_id),
            currency=STARS_CURRENCY,
            prices=[LabeledPrice(label=L.VIP_INVOICE_TITLE, amount=VIP_PRICE_STARS)],
            subscription_period=VIP_PERIOD_SECONDS,
            provider_token="",
        )
    except TelegramAPIError:
        return text + "\n\n" + L.VIP_LINK_ERROR, None
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=L.VIP_BUY_BUTTON.format(price=VIP_PRICE_STARS), url=link)]]
    )
    return text, kb


@router.message(Command("vip"))
async def cmd_vip(message: Message, bot: Bot, UL=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    text, kb = await vip_view(bot, message.from_user.id, UL)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "menu:vip")
async def on_menu_vip(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    text, kb = await vip_view(bot, callback.from_user.id, UL)
    await callback.message.answer(text, reply_markup=kb)
