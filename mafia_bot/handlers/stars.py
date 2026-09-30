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
import owner_share
import purchases
import texts
import vip
from config import ADMIN_IDS, SUPPORT_USERNAME, TIMEZONE_OFFSET_HOURS
from economy import (
    FIRST_PURCHASE_MULTIPLIER,
    GROUP_PREMIUM_PRICE_STARS,
    STARS_CURRENCY,
    STARS_PACKAGES,
    STARTER_PACK_DIAMONDS,
    STARTER_PACK_PRICE_STARS,
    VIP_PRICE_STARS,
)
from i18n import get_texts, group_lang, texts_for_user
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
async def on_pre_checkout(query: PreCheckoutQuery, bot: Bot, UL=texts) -> None:
    # Telegram 10 soniya ichida javob kutadi — shu yerda faqat tez tekshiruvlar.
    payload, currency, total, payer = query.invoice_payload, query.currency, query.total_amount, query.from_user.id
    ok = (
        validate_payment(payload, currency, total, payer) is not None
        or validate_vip(payload, currency, total, payer)
        or await purchases.validate_starter(payload, currency, total, payer)
        or purchases.validate_gift(payload, currency, total, payer) is not None
        or await purchases.validate_group_premium(bot, payload, currency, total, payer) is not None
    )
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message=UL.PRECHECKOUT_ERROR)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, bot: Bot, UL=texts) -> None:
    payload = message.successful_payment.invoice_payload
    if vip.parse_payload(payload) is not None:
        await _on_vip_payment(message, bot, UL)
    elif purchases.parse_starter(payload) is not None:
        await _on_starter_payment(message, bot, UL)
    elif purchases.parse_gift(payload) is not None:
        await _on_gift_payment(message, bot, UL)
    elif purchases.parse_group_premium(payload) is not None:
        await _on_group_premium_payment(message, bot, UL)
    else:
        await _on_package_payment(message, bot, UL)


async def _bad_payment(bot: Bot, payload: str, charge_id: str) -> None:
    # pre_checkout'dan o'tgan bo'lishi kerak edi — bu holatda hech narsa avtomatik berilmaydi, admin tekshiradi.
    logger.error("Noma'lum Stars to'lovi: %s %s", payload, charge_id)
    await _notify_admins(bot, "STARS_PAYMENT_BAD", payload=esc(payload), charge_id=esc(charge_id))


async def _on_package_payment(message: Message, bot: Bot, UL) -> None:
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    payer = message.from_user
    checked = validate_payment(payment.invoice_payload, payment.currency, payment.total_amount, payer.id)
    if checked is None:
        await _bad_payment(bot, payment.invoice_payload, charge_id)
        return
    base, stars = checked
    await db.ensure_user(payer.id, payer.full_name, payer.username)
    # ✨ Birinchi Stars olmos paketi — ×2 (karta orqali oldin xarid qilganlarga ham).
    first = await purchases.is_first_package_purchase(payer.id)
    diamonds = purchases.package_diamonds(base, first)
    if not await db.record_star_payment(charge_id, payer.id, diamonds, stars, payment.invoice_payload):
        return  # shu to'lov allaqachon hisoblangan
    text = UL.STARS_PAYMENT_OK.format(diamonds=diamonds, charge_id=esc(charge_id))
    if first:
        text += "\n" + UL.FIRST_PURCHASE_BONUS.format(multiplier=FIRST_PURCHASE_MULTIPLIER)
    await message.answer(text)
    await purchases.reward_referrer(bot, charge_id, payer.id)
    await purchases.give_owner_share(bot, charge_id, payer.id, base)
    await _notify_admins(
        bot, "STARS_PAYMENT_ADMIN",
        name=esc(payer.full_name), user_id=payer.id, diamonds=diamonds, stars=stars, charge_id=esc(charge_id),
    )


async def _on_starter_payment(message: Message, bot: Bot, UL) -> None:
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    payer = message.from_user
    parsed_ok = (
        purchases.parse_starter(payment.invoice_payload) == payer.id
        and payment.currency == STARS_CURRENCY
        and payment.total_amount == STARTER_PACK_PRICE_STARS
    )
    if not parsed_ok:
        await _bad_payment(bot, payment.invoice_payload, charge_id)
        return
    await db.ensure_user(payer.id, payer.full_name, payer.username)
    if not await db.record_star_payment(
        charge_id, payer.id, STARTER_PACK_DIAMONDS, payment.total_amount, payment.invoice_payload, kind="starter"
    ):
        return
    await purchases.give_starter_extras(charge_id, payer.id)
    await message.answer(UL.STARTER_PACK_BOUGHT.format(charge_id=esc(charge_id)))
    await purchases.reward_referrer(bot, charge_id, payer.id)
    await purchases.give_owner_share(bot, charge_id, payer.id, STARTER_PACK_DIAMONDS)
    await _notify_admins(
        bot, "STARS_PAYMENT_ADMIN", name=esc(payer.full_name), user_id=payer.id,
        diamonds=STARTER_PACK_DIAMONDS, stars=payment.total_amount, charge_id=esc(charge_id),
    )


async def _on_gift_payment(message: Message, bot: Bot, UL) -> None:
    """💝 Sovg'a: olmos qabul qiluvchiga (×2 yo'q), to'lovchining "birinchi xaridi" hisoblanmaydi,
    do'st taklifi mukofoti yo'q, guruh egasi ulushi esa hisoblanadi."""
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    payer = message.from_user
    checked = purchases.validate_gift(payment.invoice_payload, payment.currency, payment.total_amount, payer.id)
    if checked is None or await db.get_user(checked[1]) is None:
        await _bad_payment(bot, payment.invoice_payload, charge_id)
        return
    diamonds, recipient_id = checked
    await db.ensure_user(payer.id, payer.full_name, payer.username)
    if not await db.record_star_payment(
        charge_id, recipient_id, diamonds, payment.total_amount, payment.invoice_payload, payer_id=payer.id, kind="gift"
    ):
        return
    recipient = await db.get_user(recipient_id)
    await message.answer(
        UL.GIFT_SENT.format(name=esc(recipient["full_name"]), diamonds=diamonds, charge_id=esc(charge_id))
    )
    await purchases.notify_gift(bot, recipient_id, payer.full_name, diamonds)
    await purchases.give_owner_share(bot, charge_id, payer.id, diamonds)
    await _notify_admins(
        bot, "STARS_PAYMENT_ADMIN", name=esc(payer.full_name), user_id=payer.id,
        diamonds=diamonds, stars=payment.total_amount, charge_id=esc(charge_id),
    )


async def _on_group_premium_payment(message: Message, bot: Bot, UL) -> None:
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    payer = message.from_user
    parsed = purchases.parse_group_premium(payment.invoice_payload)
    if (
        not parsed or parsed[1] != payer.id or payment.currency != STARS_CURRENCY
        or payment.total_amount != GROUP_PREMIUM_PRICE_STARS
    ):
        await _bad_payment(bot, payment.invoice_payload, charge_id)
        return
    chat_id = parsed[0]
    await db.ensure_user(payer.id, payer.full_name, payer.username)
    if not await db.record_star_payment(
        charge_id, payer.id, 0, payment.total_amount, payment.invoice_payload, kind="group_premium"
    ):
        return
    await db.add_payment_grant(charge_id, payer.id, "group_premium", str(chat_id))
    until = await purchases.activate_group_premium(chat_id, payer.id, charge_id, payment.subscription_expiration_date)
    date = datetime.fromtimestamp(until, _TZ).strftime("%d.%m.%Y")
    await message.answer(UL.GROUP_PREMIUM_ACTIVATED.format(date=date))
    try:
        group_texts = get_texts(await group_lang(chat_id))
        await bot.send_message(chat_id, group_texts.GROUP_PREMIUM_GROUP_NOTICE.format(date=date))
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
    await _notify_admins(
        bot, "VIP_PAYMENT_ADMIN", name=esc(payer.full_name), user_id=payer.id,
        stars=payment.total_amount, charge_id=esc(charge_id),
    )


@router.message(F.refunded_payment)
async def on_refunded_payment(message: Message, bot: Bot) -> None:
    """Pul bot orqali emas (masalan Telegram nizo natijasida) qaytarilganda: olmosni yechamiz."""
    charge_id = message.refunded_payment.telegram_payment_charge_id
    payment = await db.get_star_payment(charge_id)
    if not payment or not await db.set_star_payment_status(charge_id, "paid", "refunded"):
        return  # noma'lum yoki bot o'zi qaytargan to'lov
    taken = await _take_diamonds(payment["user_id"], payment["diamonds"], allow_partial=True)
    await _revert_grants(charge_id)
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
    payer_id = payment["payer_id"] or user_id
    taken = await _take_diamonds(user_id, diamonds, allow_partial=force)
    if taken is None:
        await db.set_star_payment_status(charge_id, "refunding", "paid")
        return L.REFUND_NOT_ENOUGH.format(diamonds=diamonds, charge_id=esc(charge_id))

    try:
        # Stars har doim to'lagan kishiga qaytadi (sovg'ada olmos esa qabul qiluvchidan yechiladi).
        await bot.refund_star_payment(user_id=payer_id, telegram_payment_charge_id=charge_id)
    except TelegramAPIError as e:
        if taken:
            await db.add_balance(user_id, diamonds=taken)
        await db.set_star_payment_status(charge_id, "refunding", "paid")
        return L.REFUND_API_ERROR.format(error=esc(str(e)))

    await db.set_star_payment_status(charge_id, "refunding", "refunded")
    await _revert_grants(charge_id)
    try:
        user_texts = await texts_for_user(user_id)
        await bot.send_message(user_id, user_texts.REFUND_USER_NOTICE.format(stars=stars, taken=taken))
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
    return L.REFUND_DONE.format(stars=stars, taken=taken, charge_id=esc(charge_id))


async def _take_diamonds(user_id: int, diamonds: int, allow_partial: bool) -> int | None:
    if diamonds <= 0:
        return 0
    return await db.take_diamonds(user_id, diamonds, allow_partial=allow_partial)


async def _revert_grants(charge_id: str) -> None:
    """To'lov bilan berilgan qo'shimcha narsalarni (jurnal bo'yicha) qaytarib oladi."""
    for grant in await db.payment_grants(charge_id):
        user_id, kind, key, amount = grant["user_id"], grant["kind"], grant["key"], grant["amount"]
        if kind == "diamond":
            await db.take_diamonds(user_id, amount, allow_partial=True)
        elif kind == "item":
            await db.take_item(user_id, key, amount)
        elif kind == "vip":
            await vip.revoke(user_id)
        elif kind == "cosmetic":
            await db.revoke_cosmetic(user_id, key)
        elif kind == "share":
            await owner_share.revert(user_id, amount)
        elif kind == "group_premium":
            await purchases.revoke_group_premium(int(key))


def validate_vip(payload: str, currency: str, total_amount: int, payer_id: int) -> bool:
    return (
        vip.parse_payload(payload) == payer_id and currency == STARS_CURRENCY and total_amount == VIP_PRICE_STARS
    )


async def _on_vip_payment(message: Message, bot: Bot, UL) -> None:
    """VIP obunasi: birinchi to'lov va har 30 kunlik avtomatik yangilanish shu yerga keladi."""
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    user_id = message.from_user.id
    if not validate_vip(payment.invoice_payload, payment.currency, payment.total_amount, user_id):
        await _notify_admins(bot, "STARS_PAYMENT_BAD", payload=esc(payment.invoice_payload), charge_id=esc(charge_id))
        return
    await db.ensure_user(user_id, message.from_user.full_name, message.from_user.username)
    if not await db.record_star_payment(charge_id, user_id, 0, payment.total_amount, payment.invoice_payload, kind="vip"):
        return
    await db.add_payment_grant(charge_id, user_id, "vip")
    until = await vip.activate(user_id, charge_id, payment.subscription_expiration_date)
    await purchases.reward_referrer(bot, charge_id, user_id)
    date = datetime.fromtimestamp(until, _TZ).strftime("%d.%m.%Y")
    renewal = payment.is_recurring and not payment.is_first_recurring
    await message.answer((UL.VIP_RENEWED if renewal else UL.VIP_ACTIVATED).format(date=date))
    await _notify_admins(
        bot, "VIP_PAYMENT_ADMIN", name=esc(message.from_user.full_name), user_id=user_id,
        stars=payment.total_amount, charge_id=esc(charge_id),
    )


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
