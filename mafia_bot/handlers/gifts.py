"""🌱 Boshlang'ich to'plam, 🎁 olmos sovg'a qilish (Stars) va 🔗 do'st taklif qilish (/taklif)."""
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message

import db
import purchases
import texts
from economy import (
    REFERRAL_REWARD_DIAMONDS,
    STARS_CURRENCY,
    STARS_PACKAGES,
    STARTER_PACK_DIAMONDS,
    STARTER_PACK_PRICE_STARS,
    STARTER_PACK_TITLE,
)
from handlers.shop import starter_items_text
from utils import esc

router = Router(name="gifts")
STARS_PRICES = dict(STARS_PACKAGES)


class Gift(StatesGroup):
    recipient = State()


async def _send_invoice(callback: CallbackQuery, bot: Bot, **invoice) -> None:
    """Hisob-faktura har doim shaxsiy chatga; bot bloklangan bo'lsa — botga o'tish havolasi."""
    try:
        await bot.send_invoice(chat_id=callback.from_user.id, currency=STARS_CURRENCY, provider_token="", **invoice)
    except (TelegramForbiddenError, TelegramBadRequest):
        me = await bot.get_me()
        await callback.answer(url=f"https://t.me/{me.username}?start=shop")
        return
    await callback.answer()


# ---------- 🌱 Boshlang'ich to'plam ----------


@router.callback_query(F.data == "stars:starter")
async def on_starter(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    user_id = callback.from_user.id
    await db.ensure_user(user_id, callback.from_user.full_name, callback.from_user.username)
    if not await purchases.starter_available(user_id):
        await callback.answer(UL.STARTER_NOT_AVAILABLE, show_alert=True)
        return
    description = UL.STARTER_INVOICE_DESCRIPTION.format(
        diamonds=STARTER_PACK_DIAMONDS, items=starter_items_text(UL), title=UL.COSMETIC_NAMES[STARTER_PACK_TITLE]
    )
    await _send_invoice(
        callback, bot,
        title=UL.STARTER_INVOICE_TITLE,
        description=description,
        payload=purchases.starter_payload(user_id),
        prices=[LabeledPrice(label=UL.STARTER_INVOICE_TITLE, amount=STARTER_PACK_PRICE_STARS)],
    )


# ---------- 🎁 Sovg'a ----------


@router.callback_query(F.data == "stars:gift")
async def on_gift(callback: CallbackQuery, state: FSMContext, UL=texts) -> None:
    if callback.message.chat.type != "private":
        # Guruhda boshlansa, keyingi har bir guruh xabari qabul qiluvchi deb o'qib qolinardi.
        await callback.answer(UL.GIFT_PRIVATE_ONLY, show_alert=True)
        return
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    await state.set_state(Gift.recipient)
    await callback.message.answer(UL.GIFT_ASK_RECIPIENT)


async def find_recipient(raw: str):
    raw = raw.strip()
    if raw.lstrip("-").isdigit():
        return await db.get_user(int(raw))
    username = raw.removeprefix("@").removeprefix("https://t.me/")
    return await db.get_user_by_username(username) if username else None


def gift_packages_keyboard(recipient_id: int, L=texts) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=L.SHOP_STARS_BUTTON.format(diamonds=diamonds, stars=stars),
            callback_data=f"stars:giftto:{diamonds}:{recipient_id}",
        )
        for diamonds, stars in STARS_PACKAGES
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[i : i + 2] for i in range(0, len(buttons), 2)])


@router.message(Gift.recipient, F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def on_gift_recipient(message: Message, state: FSMContext, L=texts) -> None:
    recipient = await find_recipient(message.text)
    if recipient is None:
        await message.answer(L.GIFT_RECIPIENT_NOT_FOUND)
        return
    if recipient["user_id"] == message.from_user.id:
        await message.answer(L.GIFT_SELF)
        return
    await state.clear()
    await message.answer(
        L.GIFT_CHOOSE_PACKAGE.format(name=esc(recipient["full_name"])),
        reply_markup=gift_packages_keyboard(recipient["user_id"], L),
    )


@router.callback_query(F.data.startswith("stars:giftto:"))
async def on_gift_package(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit() or int(parts[2]) not in STARS_PRICES:
        await callback.answer(UL.PACKAGE_NOT_FOUND, show_alert=True)
        return
    diamonds, recipient_id = int(parts[2]), int(parts[3])
    recipient = await db.get_user(recipient_id)
    if recipient is None:
        await callback.answer(UL.GIFT_RECIPIENT_NOT_FOUND, show_alert=True)
        return
    if recipient_id == callback.from_user.id:
        await callback.answer(UL.GIFT_SELF, show_alert=True)
        return
    name = recipient["full_name"]
    await _send_invoice(
        callback, bot,
        title=UL.GIFT_INVOICE_TITLE.format(diamonds=diamonds),
        description=UL.GIFT_INVOICE_DESCRIPTION.format(name=name, diamonds=diamonds),
        payload=purchases.gift_payload(diamonds, recipient_id, callback.from_user.id),
        prices=[LabeledPrice(label=UL.GIFT_INVOICE_TITLE.format(diamonds=diamonds), amount=STARS_PRICES[diamonds])],
    )


# ---------- 🔗 Do'st taklifi ----------


async def referral_text(bot: Bot, user_id: int, L=texts) -> str:
    me = await bot.get_me()
    count, rewarded = await db.referral_count(user_id)
    return L.REFERRAL_TEXT.format(
        link=f"https://t.me/{me.username}?start=ref_{user_id}",
        diamonds=REFERRAL_REWARD_DIAMONDS, count=count, rewarded=rewarded,
    )


@router.message(Command("taklif", "invite"))
async def cmd_invite(message: Message, bot: Bot, UL=texts) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(await referral_text(bot, message.from_user.id, UL), disable_web_page_preview=True)


@router.callback_query(F.data == "menu:invite")
async def on_menu_invite(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    await callback.message.answer(await referral_text(bot, callback.from_user.id, UL), disable_web_page_preview=True)
