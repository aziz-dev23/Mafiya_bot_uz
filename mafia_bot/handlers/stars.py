"""Telegram Stars (XTR) orqali olmos sotish: hisob-faktura, pre_checkout tekshiruvi, to'lovni qabul qilish,
pulni qaytarish va Telegram talab qiladigan /paysupport, /support, /terms buyruqlari.
https://core.telegram.org/bots/payments-stars"""
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

import db
import texts
from config import ADMIN_IDS, SUPPORT_USERNAME, TIMEZONE_OFFSET_HOURS
from economy import STARS_CURRENCY, STARS_PACKAGES
from i18n import texts_for_user
from utils import esc

logger = logging.getLogger(__name__)
router = Router(name="stars")

_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))
PAYLOAD_PREFIX = "stars"
STARS_PRICES = dict(STARS_PACKAGES)


def build_payload(diamonds: int, user_id: int) -> str:
    return f"{PAYLOAD_PREFIX}:{diamonds}:{user_id}"


def parse_payload(payload: str) -> tuple[int, int] | None:
    """(olmos, user_id) yoki payload noto'g'ri bo'lsa None."""
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != PAYLOAD_PREFIX or not parts[1].isdigit() or not parts[2].isdigit():
        return None
    diamonds, user_id = int(parts[1]), int(parts[2])
    if diamonds not in STARS_PRICES:
        return None
    return diamonds, user_id


def validate_payment(payload: str, currency: str, total_amount: int, payer_id: int) -> tuple[int, int] | None:
    """To'lov bizning paketlarimizdan biriga to'liq mos kelsa (olmos, stars), aks holda None."""
    parsed = parse_payload(payload)
    if parsed is None or currency != STARS_CURRENCY:
        return None
    diamonds, user_id = parsed
    stars = STARS_PRICES[diamonds]
    if total_amount != stars or payer_id != user_id:
        return None
    return diamonds, stars


async def _notify_admins(bot: Bot, key: str, **fields) -> None:
    """Adminlarga xabar — har biriga o'z tilida."""
    for admin_id in ADMIN_IDS:
        text = getattr(await texts_for_user(admin_id), key).format(**fields)
        try:
            await bot.send_message(admin_id, text)
        except (TelegramForbiddenError, TelegramBadRequest):
            pass


@router.callback_query(F.data.startswith("stars:buy:"))
async def on_buy_stars(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    raw = callback.data.rsplit(":", 1)[1]
    diamonds = int(raw) if raw.isdigit() else None
    if diamonds not in STARS_PRICES:
        await callback.answer(UL.PACKAGE_NOT_FOUND, show_alert=True)
        return
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    try:
        # Hisob-faktura har doim shaxsiy chatga — guruhda boshqa odam to'lab yubormasligi uchun.
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=UL.INVOICE_TITLE.format(diamonds=diamonds),
            description=UL.INVOICE_DESCRIPTION.format(diamonds=diamonds),
            payload=build_payload(diamonds, callback.from_user.id),
            currency=STARS_CURRENCY,
            prices=[LabeledPrice(label=UL.INVOICE_LABEL.format(diamonds=diamonds), amount=STARS_PRICES[diamonds])],
            provider_token="",  # Stars uchun bo'sh
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        me = await bot.get_me()
        await callback.answer(url=f"https://t.me/{me.username}?start=shop")
        return
    await callback.answer()


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery, UL=texts) -> None:
    # Telegram 10 soniya ichida javob kutadi — shu yerda faqat tez tekshiruvlar.
    ok = validate_payment(query.invoice_payload, query.currency, query.total_amount, query.from_user.id) is not None
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message=UL.PRECHECKOUT_ERROR)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, bot: Bot, UL=texts) -> None:
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    checked = validate_payment(payment.invoice_payload, payment.currency, payment.total_amount, message.from_user.id)
    if checked is None:
        # pre_checkout'dan o'tgan bo'lishi kerak edi — bu holatda olmos avtomatik berilmaydi, admin tekshiradi.
        logger.error("Noma'lum Stars to'lovi: %s %s", payment.invoice_payload, charge_id)
        await _notify_admins(bot, "STARS_PAYMENT_BAD", payload=esc(payment.invoice_payload), charge_id=esc(charge_id))
        return
    diamonds, stars = checked

    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    if not await db.record_star_payment(charge_id, message.from_user.id, diamonds, stars, payment.invoice_payload):
        return  # shu to'lov allaqachon hisoblangan
    await message.answer(UL.STARS_PAYMENT_OK.format(diamonds=diamonds, charge_id=esc(charge_id)))
    await _notify_admins(
        bot, "STARS_PAYMENT_ADMIN",
        name=esc(message.from_user.full_name), user_id=message.from_user.id,
        diamonds=diamonds, stars=stars, charge_id=esc(charge_id),
    )


@router.message(F.refunded_payment)
async def on_refunded_payment(message: Message, bot: Bot) -> None:
    """Pul bot orqali emas (masalan Telegram nizo natijasida) qaytarilganda: olmosni yechamiz."""
    charge_id = message.refunded_payment.telegram_payment_charge_id
    payment = await db.get_star_payment(charge_id)
    if not payment or not await db.set_star_payment_status(charge_id, "paid", "refunded"):
        return  # noma'lum yoki bot o'zi qaytargan to'lov
    taken = await db.take_diamonds(payment["user_id"], payment["diamonds"], allow_partial=True)
    await _notify_admins(
        bot, "REFUND_EXTERNAL_ADMIN",
        user_id=payment["user_id"], stars=payment["stars"], taken=taken, diamonds=payment["diamonds"],
        charge_id=esc(charge_id),
    )


async def refund_payment(bot: Bot, charge_id: str, force: bool, L=texts) -> str:
    """Admin uchun: Stars'ni qaytaradi va olmosni yechadi. Natija matnini qaytaradi."""
    payment = await db.get_star_payment(charge_id)
    if not payment:
        return L.REFUND_NOT_FOUND
    # Avval holatni "qaytarilmoqda" ga o'tkazamiz — bir vaqtda ikki marta qaytarib bo'lmaydi.
    if not await db.set_star_payment_status(charge_id, "paid", "refunding"):
        return L.REFUND_WRONG_STATUS.format(status=L.PAYMENT_STATUS_NAMES.get(payment["status"], payment["status"]))

    user_id, diamonds, stars = payment["user_id"], payment["diamonds"], payment["stars"]
    taken = await db.take_diamonds(user_id, diamonds, allow_partial=force)
    if taken is None:
        await db.set_star_payment_status(charge_id, "refunding", "paid")
        return L.REFUND_NOT_ENOUGH.format(diamonds=diamonds, charge_id=esc(charge_id))

    try:
        await bot.refund_star_payment(user_id=user_id, telegram_payment_charge_id=charge_id)
    except TelegramAPIError as e:
        if taken:
            await db.add_balance(user_id, diamonds=taken)
        await db.set_star_payment_status(charge_id, "refunding", "paid")
        return L.REFUND_API_ERROR.format(error=esc(str(e)))

    await db.set_star_payment_status(charge_id, "refunding", "refunded")
    try:
        user_texts = await texts_for_user(user_id)
        await bot.send_message(user_id, user_texts.REFUND_USER_NOTICE.format(stars=stars, taken=taken))
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
    return L.REFUND_DONE.format(stars=stars, taken=taken, charge_id=esc(charge_id))


@router.message(Command("refund"))
async def cmd_refund(message: Message, bot: Bot, command: CommandObject, L=texts) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    args = (command.args or "").split()
    if not args:
        await message.answer(L.REFUND_USAGE)
        return
    force = len(args) > 1 and args[1].lower() == "force"
    await message.answer(await refund_payment(bot, args[0], force, L))


@router.message(Command("paysupport"))
async def cmd_paysupport(message: Message, L=texts) -> None:
    lines = [L.PAYSUPPORT_TEXT.format(support=SUPPORT_USERNAME), ""]
    payments = await db.user_star_payments(message.from_user.id)
    if not payments:
        lines.append(L.PAYSUPPORT_NO_PAYMENTS)
    else:
        lines.append(L.PAYSUPPORT_PAYMENTS_HEADER)
        for p in payments:
            lines.append(
                L.PAYSUPPORT_PAYMENT_LINE.format(
                    date=datetime.fromtimestamp(p["created_at"], _TZ).strftime("%d.%m.%Y %H:%M"),
                    diamonds=p["diamonds"], stars=p["stars"],
                    status=L.PAYMENT_STATUS_NAMES.get(p["status"], p["status"]),
                    charge_id=esc(p["charge_id"]),
                )
            )
    await message.answer("\n".join(lines))


@router.message(Command("support"))
async def cmd_support(message: Message, L=texts) -> None:
    await message.answer(L.SUPPORT_TEXT.format(support=SUPPORT_USERNAME))


@router.message(Command("terms"))
async def cmd_terms(message: Message, L=texts) -> None:
    await message.answer(L.TERMS_TEXT)
