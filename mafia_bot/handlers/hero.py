from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from economy import HERO_BUY_PRICE_DIAMONDS, HERO_BYPASS_LEVEL, HERO_LEVEL_UP_PRICE_DIAMONDS

router = Router(name="hero")


async def build_hero_view(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    level = await db.get_hero_level(user_id)

    if level == 0:
        text = (
            "🦸 <b>GEROY</b>\n\n"
            "Geroy — bir marta sotib olinadigan va profilingizda umrbod qoladigan maxsus buyum.\n"
            "Darajasini cheksiz oshirish mumkin.\n\n"
            f"🎭 Mafiya, Don yoki Komissar bo'lib qolgan o'yinlarda tongda nishonni otish huquqi beradi.\n"
            f"🔓 {HERO_BYPASS_LEVEL}-darajadan boshlab zarbangiz HAR QANDAY himoyani chetlab o'tadi.\n\n"
            f"Narxi: {HERO_BUY_PRICE_DIAMONDS}💎"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"🦸 Sotib olish — {HERO_BUY_PRICE_DIAMONDS}💎", callback_data="hero:buy")]
            ]
        )
        return text, kb

    if level >= HERO_BYPASS_LEVEL:
        bypass_line = "🔓 Zarbangiz har qanday himoyani chetlab o'tadi!"
    else:
        bypass_line = f"🔒 {HERO_BYPASS_LEVEL}-darajaga yetganda zarbangiz har qanday himoyani chetlab o'tadi."

    text = (
        "🦸 <b>GEROY</b>\n\n"
        f"Joriy darajangiz: <b>{level}</b>\n"
        f"{bypass_line}\n\n"
        f"Darajani oshirish narxi: {HERO_LEVEL_UP_PRICE_DIAMONDS}💎"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⬆️ Darajani oshirish — {HERO_LEVEL_UP_PRICE_DIAMONDS}💎",
                    callback_data="hero:levelup",
                )
            ]
        ]
    )
    return text, kb


@router.message(Command("geroy", "hero"))
async def cmd_hero(message: Message) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    text, kb = await build_hero_view(message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "hero:buy")
async def on_hero_buy(callback: CallbackQuery) -> None:
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    level = await db.get_hero_level(callback.from_user.id)
    if level > 0:
        await callback.answer("Sizda allaqachon Geroy bor.", show_alert=True)
        return

    user_row = await db.get_user(callback.from_user.id)
    if user_row["diamonds"] < HERO_BUY_PRICE_DIAMONDS:
        await callback.answer("Balansingizda yetarli 💎 yo'q.", show_alert=True)
        return

    await db.add_balance(callback.from_user.id, diamonds=-HERO_BUY_PRICE_DIAMONDS)
    await db.set_hero_level(callback.from_user.id, 1)
    await callback.answer("✅ Geroy sotib olindi!")

    text, kb = await build_hero_view(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "hero:levelup")
async def on_hero_levelup(callback: CallbackQuery) -> None:
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    level = await db.get_hero_level(callback.from_user.id)
    if level <= 0:
        await callback.answer("Avval Geroyni sotib oling.", show_alert=True)
        return

    user_row = await db.get_user(callback.from_user.id)
    if user_row["diamonds"] < HERO_LEVEL_UP_PRICE_DIAMONDS:
        await callback.answer("Balansingizda yetarli 💎 yo'q.", show_alert=True)
        return

    await db.add_balance(callback.from_user.id, diamonds=-HERO_LEVEL_UP_PRICE_DIAMONDS)
    await db.set_hero_level(callback.from_user.id, level + 1)
    await callback.answer(f"✅ Geroy {level + 1}-darajaga o'tdi!")

    text, kb = await build_hero_view(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
