from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import db
from config import PAYMENT_CARD_NUMBER
from handlers import admin, clan, items, market, shop
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
                InlineKeyboardButton(text="🏰 Mening klanim", callback_data="menu:clan"),
            ],
            [
                InlineKeyboardButton(text="🛒 Do'kon", callback_data="menu:store"),
                InlineKeyboardButton(text="🛍 Bozor", callback_data="menu:market"),
            ],
            [
                InlineKeyboardButton(text="💎 Olmos sotib olish", callback_data="menu:shop"),
                InlineKeyboardButton(text="🏆 Top klanlar", callback_data="menu:topclans"),
            ],
            [
                InlineKeyboardButton(text="💸 Pul yuborish", callback_data="menu:send_dollar"),
                InlineKeyboardButton(text="💎 Olmos yuborish", callback_data="menu:send_diamond"),
            ],
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


@router.callback_query(F.data == "menu:clan")
async def on_clan(callback: CallbackQuery) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    clan_row = await db.get_user_clan(callback.from_user.id)
    if not clan_row:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🏰 Klan yaratish", callback_data="clan:create_start")]]
        )
        await callback.message.answer(
            "Siz hali hech qanday klanga a'zo emassiz.\n\n"
            f"Klan ochish narxi: {clan.CLAN_CREATE_COST_DIAMONDS} 💎 YOKI "
            f"{clan.CLAN_CREATE_COST_DOLLARS} 💵",
            reply_markup=_with_back(kb),
        )
        return
    await callback.message.answer(await clan.build_clan_card(clan_row), reply_markup=_with_back(None))


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


@router.callback_query(F.data == "menu:topclans")
async def on_topclans(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(await clan.build_topclans_text(), reply_markup=_with_back(None))


@router.callback_query(F.data == "menu:help")
async def on_help(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(HELP_TEXT, reply_markup=_with_back(None))
