from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import db
import texts
from handlers import admin, items, market, shop

router = Router(name="menu")

# Guruhga qo'shishda so'raladigan admin huquqlari: xabarlarni o'chirish, cheklash, qadash.
ADD_TO_GROUP_ADMIN_RIGHTS = "delete_messages+restrict_members+pin_messages"


def main_menu_text(L=texts) -> str:
    return f"{L.MAIN_MENU_TEXT}\n\n{L.ADD_TO_GROUP_RIGHTS}"


def _with_back(kb: InlineKeyboardMarkup | None, L=texts) -> InlineKeyboardMarkup:
    rows = list(kb.inline_keyboard) if kb else []
    rows.append([InlineKeyboardButton(text=L.MENU_BACK, callback_data="menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_main_menu_keyboard(bot_username: str, L=texts) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=L.MENU_ADD_TO_GROUP,
                    # admin= parametri guruhga qo'shishda kerakli huquqlarni oldindan belgilab beradi.
                    url=f"https://t.me/{bot_username}?startgroup=true&admin={ADD_TO_GROUP_ADMIN_RIGHTS}",
                )
            ],
            [
                InlineKeyboardButton(text=L.MENU_PROFILE, callback_data="menu:profile"),
                InlineKeyboardButton(text=L.MENU_STORE, callback_data="menu:store"),
            ],
            [
                InlineKeyboardButton(text=L.MENU_MARKET, callback_data="menu:market"),
                InlineKeyboardButton(text=L.MENU_SHOP, callback_data="menu:shop"),
            ],
            [
                InlineKeyboardButton(text=L.MENU_SEND_DOLLAR, callback_data="menu:send_dollar"),
                InlineKeyboardButton(text=L.MENU_SEND_DIAMOND, callback_data="menu:send_diamond"),
            ],
            [InlineKeyboardButton(text=L.MENU_EXCHANGE_BUTTON, callback_data="menu:exchange")],
            [
                InlineKeyboardButton(text=L.MENU_HELP, callback_data="menu:help"),
                InlineKeyboardButton(text=L.MENU_LANGUAGE, callback_data="lang:menu"),
            ],
        ]
    )


@router.callback_query(F.data == "menu:back")
async def on_back(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    me = await bot.get_me()
    await callback.answer()
    kb = build_main_menu_keyboard(me.username, UL)
    try:
        await callback.message.edit_text(main_menu_text(UL), reply_markup=kb)
    except TelegramBadRequest:
        await callback.message.answer(main_menu_text(UL), reply_markup=kb)


@router.callback_query(F.data == "menu:profile")
async def on_profile(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    text, kb = await admin.build_profile_view(
        callback.from_user.id, callback.from_user.full_name, callback.from_user.username, UL
    )
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "menu:store")
async def on_store(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    await callback.message.answer(items.store_text(UL), reply_markup=_with_back(items.build_store_keyboard(UL), UL))


@router.callback_query(F.data == "menu:market")
async def on_market(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    text, kb = await market.build_market_view(UL)
    await callback.message.answer(text, reply_markup=_with_back(kb, UL))


@router.callback_query(F.data == "menu:shop")
async def on_shop(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    text, kb = shop.shop_view(UL)
    await callback.message.answer(text, reply_markup=_with_back(kb, UL))


@router.callback_query(F.data == "menu:exchange")
async def on_exchange(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    await callback.message.answer(shop.exchange_text(UL), reply_markup=_with_back(shop.build_exchange_keyboard(), UL))


@router.callback_query(F.data == "menu:help")
async def on_help(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    await callback.message.answer(UL.HELP_TEXT, reply_markup=_with_back(None, UL))
