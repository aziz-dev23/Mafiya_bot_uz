from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import db
from config import PAYMENT_CARD_NUMBER
from economy import DIAMOND_TO_DOLLAR_RATE
from handlers import admin, items, market, shop
from texts import HELP_TEXT

router = Router(name="menu")

MAIN_MENU_TEXT = (
    "🎩 <b>Qorong'u shaharga xush kelibsiz!</b>\n\n"
    "<i>Bu yerda oddiy qoidalar ishlamaydi. Do'stlik, xiyonat va intriga — "
    "barchasi bir-biriga qorishib ketgan.</i>\n\n"
    "🛡 <b>Tinch aholi</b> bo'lib shaharni qutqarasizmi yoki 🔪 <b>Mafiya</b> bo'lib "
    "hammani yo'q qilasizmi?\n\n"
    "Guruhga qo'shing va <code>/mafia</code> yozing yoki pastdagi tugmalardan foydalaning 👇"
)

BACK_BUTTON = InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="menu:back")


def _with_back(kb: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup:
    rows = list(kb.inline_keyboard) if kb else []
    rows.append([BACK_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_main_menu_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Guruhingizga qo'shish",
                    url=f"https://t.me/{bot_username}?startgroup=true",
                )
            ],
            [
                InlineKeyboardButton(text="👤 Mening profilim", callback_data="menu:profile"),
                InlineKeyboardButton(text="🛒 Do'kon", callback_data="menu:store"),
            ],
            [
                InlineKeyboardButton(text="🛍 Bozor", callback_data="menu:market"),
                InlineKeyboardButton(text="💎 Olmos sotib olish", callback_data="menu:shop"),
            ],
            [
                InlineKeyboardButton(text="💸 Pul yuborish", callback_data="menu:send_dollar"),
                InlineKeyboardButton(text="💎 Olmos yuborish", callback_data="menu:send_diamond"),
            ],
            [InlineKeyboardButton(text="💱 Olmosni pulga almashtirish", callback_data="menu:exchange")],
            [InlineKeyboardButton(text="❓ Yordam", callback_data="menu:help")],
        ]
    )


@router.callback_query(F.data == "menu:back")
async def on_back(callback: CallbackQuery, bot: Bot) -> None:
    me = await bot.get_me()
    await callback.answer()
    try:
        await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=build_main_menu_keyboard(me.username))
    except TelegramBadRequest:
        await callback.message.answer(MAIN_MENU_TEXT, reply_markup=build_main_menu_keyboard(me.username))


@router.callback_query(F.data == "menu:profile")
async def on_profile(callback: CallbackQuery) -> None:
    await callback.answer()
    text, kb = await admin.build_profile_view(
        callback.from_user.id, callback.from_user.full_name, callback.from_user.username
    )
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "menu:store")
async def on_store(callback: CallbackQuery) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    await callback.message.answer(
        "🎒 <b>BUYUMLAR DO'KONI</b>\n"
        "O'yin ichida foydali bo'ladigan buyumlarni sotib oling. "
        "Sotib olingan buyum avtomatik yoniq (YONIQ) holatda bo'ladi.\n\n"
        "Kerakli buyumni tanlang:",
        reply_markup=_with_back(items.build_store_keyboard()),
    )


@router.callback_query(F.data == "menu:market")
async def on_market(callback: CallbackQuery) -> None:
    await callback.answer()
    text, kb = await market.build_market_view()
    await callback.message.answer(text, reply_markup=_with_back(kb))


@router.callback_query(F.data == "menu:shop")
async def on_shop(callback: CallbackQuery) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    if not PAYMENT_CARD_NUMBER:
        await callback.message.answer(
            "Hozircha olmos sotib olish ishlamayapti, keyinroq urinib ko'ring.", reply_markup=_with_back(None)
        )
        return
    await callback.message.answer(
        "💎 <b>OLMOS DO'KONI</b>\nKerakli paketni tanlang:",
        reply_markup=_with_back(shop.build_shop_keyboard()),
    )


@router.callback_query(F.data == "menu:exchange")
async def on_exchange(callback: CallbackQuery) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    await callback.message.answer(
        "💱 <b>OLMOSNI PULGA ALMASHTIRISH</b>\n"
        f"Kurs: 1💎 = {DIAMOND_TO_DOLLAR_RATE}💵\n\nKerakli miqdorni tanlang:",
        reply_markup=_with_back(shop.build_exchange_keyboard()),
    )


@router.callback_query(F.data == "menu:help")
async def on_help(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(HELP_TEXT, reply_markup=_with_back(None))
