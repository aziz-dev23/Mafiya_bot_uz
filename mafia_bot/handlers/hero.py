from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import texts
from economy import HERO_BUY_PRICE_DIAMONDS, HERO_BYPASS_LEVEL, HERO_LEVEL_UP_PRICE_DIAMONDS

router = Router(name="hero")


async def build_hero_view(user_id: int, L=texts) -> tuple[str, InlineKeyboardMarkup]:
    level = await db.get_hero_level(user_id)

    if level == 0:
        text = L.HERO_INTRO.format(bypass=HERO_BYPASS_LEVEL, price=HERO_BUY_PRICE_DIAMONDS)
        button = InlineKeyboardButton(text=L.HERO_BUY_BUTTON.format(price=HERO_BUY_PRICE_DIAMONDS), callback_data="hero:buy")
        return text, InlineKeyboardMarkup(inline_keyboard=[[button]])

    if level >= HERO_BYPASS_LEVEL:
        bypass_line = L.HERO_BYPASS_ACTIVE
    else:
        bypass_line = L.HERO_BYPASS_LOCKED.format(level=HERO_BYPASS_LEVEL)

    text = L.HERO_STATUS.format(level=level, bypass=bypass_line, price=HERO_LEVEL_UP_PRICE_DIAMONDS)
    button = InlineKeyboardButton(
        text=L.HERO_LEVELUP_BUTTON.format(price=HERO_LEVEL_UP_PRICE_DIAMONDS), callback_data="hero:levelup"
    )
    return text, InlineKeyboardMarkup(inline_keyboard=[[button]])


@router.message(Command("geroy", "hero"))
async def cmd_hero(message: Message, L=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    text, kb = await build_hero_view(message.from_user.id, L)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "hero:buy")
async def on_hero_buy(callback: CallbackQuery, UL=texts) -> None:
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    level = await db.get_hero_level(callback.from_user.id)
    if level > 0:
        await callback.answer(UL.HERO_ALREADY_OWNED, show_alert=True)
        return

    if not await db.spend_balance(callback.from_user.id, "diamonds", HERO_BUY_PRICE_DIAMONDS):
        await callback.answer(UL.NOT_ENOUGH_DIAMONDS, show_alert=True)
        return
    if not await db.create_hero(callback.from_user.id):
        # Ikki marta tez bosilgan: Geroy allaqachon yaratilgan — ikkinchi to'lov qaytariladi.
        await db.add_balance(callback.from_user.id, diamonds=HERO_BUY_PRICE_DIAMONDS)
        await callback.answer(UL.HERO_ALREADY_OWNED, show_alert=True)
        return
    await callback.answer(UL.HERO_BOUGHT)

    text, kb = await build_hero_view(callback.from_user.id, UL)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "hero:levelup")
async def on_hero_levelup(callback: CallbackQuery, UL=texts) -> None:
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    level = await db.get_hero_level(callback.from_user.id)
    if level <= 0:
        await callback.answer(UL.HERO_BUY_FIRST, show_alert=True)
        return

    if not await db.spend_balance(callback.from_user.id, "diamonds", HERO_LEVEL_UP_PRICE_DIAMONDS):
        await callback.answer(UL.NOT_ENOUGH_DIAMONDS, show_alert=True)
        return

    new_level = await db.increment_hero_level(callback.from_user.id)
    await callback.answer(UL.HERO_LEVELED_UP.format(level=new_level))

    text, kb = await build_hero_view(callback.from_user.id, UL)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
