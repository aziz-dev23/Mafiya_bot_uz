"""Stars xaridlarining qo'shimcha qoidalari: ✨ birinchi xarid ×2, 🌱 boshlang'ich to'plam, 💝 sovg'a,
🏰 guruh premiumi, 🔗 do'st taklifi mukofoti, 🤝 guruh egasi ulushi.

Har bir qo'shimcha berilgan narsa payment_grants jurnaliga yoziladi — pul qaytarilsa (refund) hammasi
shu jurnal bo'yicha qaytarib olinadi (handlers/stars.py: _revert_grants)."""
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

import db
from economy import (
    FIRST_PURCHASE_MULTIPLIER,
    GROUP_PREMIUM_PRICE_STARS,
    OWNER_SHARE_PERCENT,
    REFERRAL_REWARD_DIAMONDS,
    STARS_CURRENCY,
    STARS_PACKAGES,
    STARTER_PACK_DIAMONDS,
    STARTER_PACK_ITEMS,
    STARTER_PACK_PRICE_STARS,
    STARTER_PACK_TITLE,
    VIP_PERIOD_SECONDS,
)
from i18n import texts_for_user
from owner_share import MILLI
from utils import esc

logger = logging.getLogger(__name__)
STARS_PRICES = dict(STARS_PACKAGES)

# Kind qiymatlari (star_payments.kind): "diamonds", "starter", "gift", "vip", "group_premium".


# ---------- Payload'lar ----------


def starter_payload(user_id: int) -> str:
    return f"starter:{user_id}"


def gift_payload(diamonds: int, recipient_id: int, payer_id: int) -> str:
    return f"gift:{diamonds}:{recipient_id}:{payer_id}"


def group_premium_payload(chat_id: int, payer_id: int) -> str:
    return f"gp:{chat_id}:{payer_id}"


def _ints(parts: list[str]) -> list[int] | None:
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None


def parse_starter(payload: str) -> int | None:
    parts = payload.split(":")
    if len(parts) == 2 and parts[0] == "starter" and parts[1].isdigit():
        return int(parts[1])
    return None


def parse_gift(payload: str) -> tuple[int, int, int] | None:
    """(olmos, qabul qiluvchi, to'lovchi)."""
    parts = payload.split(":")
    if len(parts) != 4 or parts[0] != "gift":
        return None
    values = _ints(parts[1:])
    if not values or values[0] not in STARS_PRICES:
        return None
    return values[0], values[1], values[2]


def parse_group_premium(payload: str) -> tuple[int, int] | None:
    """(chat_id, to'lovchi)."""
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "gp":
        return None
    values = _ints(parts[1:])
    return (values[0], values[1]) if values else None


# ---------- pre_checkout tekshiruvlari ----------


async def starter_available(user_id: int) -> bool:
    """🌱 faqat hech qachon hech narsa sotib olmaganlarga (karta orqali ham) ko'rinadi."""
    return not await db.has_any_purchase(user_id)


async def validate_starter(payload: str, currency: str, total: int, payer_id: int) -> bool:
    return (
        parse_starter(payload) == payer_id
        and currency == STARS_CURRENCY
        and total == STARTER_PACK_PRICE_STARS
        and await starter_available(payer_id)
    )


def validate_gift(payload: str, currency: str, total: int, payer_id: int) -> tuple[int, int] | None:
    parsed = parse_gift(payload)
    if not parsed or currency != STARS_CURRENCY:
        return None
    diamonds, recipient_id, gift_payer = parsed
    if gift_payer != payer_id or recipient_id == payer_id or total != STARS_PRICES[diamonds]:
        return None
    return diamonds, recipient_id


async def is_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramAPIError:
        return False
    return member.status in ("administrator", "creator")


async def validate_group_premium(bot: Bot, payload: str, currency: str, total: int, payer_id: int) -> int | None:
    parsed = parse_group_premium(payload)
    if not parsed or currency != STARS_CURRENCY or total != GROUP_PREMIUM_PRICE_STARS or parsed[1] != payer_id:
        return None
    return parsed[0] if await is_chat_admin(bot, parsed[0], payer_id) else None


# ---------- Xariddan keyingi qoidalar ----------


async def is_first_package_purchase(payer_id: int) -> bool:
    """✨ Birinchi Stars olmos paketi (sovg'a va boshlang'ich to'plam hisobga olinmaydi; karta ham)."""
    return await db.star_purchase_count(payer_id, ("diamonds",)) == 0


def package_diamonds(base: int, first: bool) -> int:
    return base * FIRST_PURCHASE_MULTIPLIER if first else base


async def give_starter_extras(charge_id: str, user_id: int) -> None:
    """🌱 to'plamdagi buyumlar va "Yangi o'yinchi" unvoni (olmos to'lov yozuvi bilan birga tushadi)."""
    for key, count in STARTER_PACK_ITEMS:
        await db.add_item(user_id, key, count)
        await db.add_payment_grant(charge_id, user_id, "item", key, count)
    if await db.grant_cosmetic(user_id, STARTER_PACK_TITLE):
        await db.add_payment_grant(charge_id, user_id, "cosmetic", STARTER_PACK_TITLE)
        active = await db.active_cosmetics(user_id)
        if "title" not in active:
            await db.set_active_cosmetic(user_id, "title", STARTER_PACK_TITLE)


async def reward_referrer(bot: Bot, charge_id: str, payer_id: int) -> None:
    """🔗 Taklif qilingan do'stning birinchi Stars xaridi (sovg'a emas) — taklif qilganga mukofot."""
    referrer_id = await db.claim_referral_reward(payer_id)
    if referrer_id is None:
        return
    await db.add_balance(referrer_id, diamonds=REFERRAL_REWARD_DIAMONDS)
    await db.add_payment_grant(charge_id, referrer_id, "diamond", None, REFERRAL_REWARD_DIAMONDS)
    L = await texts_for_user(referrer_id)
    await _safe_send(bot, referrer_id, L.REFERRAL_REWARD.format(diamonds=REFERRAL_REWARD_DIAMONDS))


async def resolve_group_owner(bot: Bot, chat_id: int) -> int | None:
    """Guruh egasi: yaratuvchi tayinlagan admin, aks holda guruh yaratuvchisi (getChatAdministrators)."""
    override = await db.get_group_owner_override(chat_id)
    if override:
        return override
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except TelegramAPIError:
        return None
    creator = next((a for a in admins if a.status == "creator"), None)
    return creator.user.id if creator else None


async def give_owner_share(bot: Bot, charge_id: str, payer_id: int, base_diamonds: int) -> None:
    """🤝 Xariddagi (bazaviy, ×2 bonussiz) olmosning OWNER_SHARE_PERCENT foizi to'lovchi oxirgi o'ynagan
    guruh egasiga. Egasining o'z xaridi hisoblanmaydi. Kasr qismi yig'ilib boradi."""
    if base_diamonds <= 0:
        return
    chat_id = await db.last_played_chat(payer_id)
    if chat_id is None:
        return
    owner_id = await resolve_group_owner(bot, chat_id)
    if owner_id is None or owner_id == payer_id:
        return
    millis = base_diamonds * MILLI * OWNER_SHARE_PERCENT // 100
    if millis <= 0:
        return
    await db.add_owner_share(owner_id, millis)
    await db.add_payment_grant(charge_id, owner_id, "share", None, millis)
    await settle_and_notify(bot, owner_id)


async def settle_and_notify(bot: Bot, owner_id: int) -> int:
    """Yig'ilgan butun olmoslarni hisobga o'tkazadi (egasi botga /start bosgan bo'lsa) va xabar beradi."""
    paid = await db.settle_owner_share(owner_id)
    if paid:
        L = await texts_for_user(owner_id)
        await _safe_send(bot, owner_id, L.OWNER_SHARE_PAID.format(diamonds=paid))
    return paid


async def activate_group_premium(chat_id: int, payer_id: int, charge_id: str, expiration: int | None) -> int:
    until = expiration or int(time.time()) + VIP_PERIOD_SECONDS
    until = max(until, await db.group_premium_until(chat_id))
    await db.set_group_premium(chat_id, until, payer_id, charge_id)
    return until


async def revoke_group_premium(chat_id: int) -> None:
    await db.set_group_premium(chat_id, int(time.time()), None, None)


async def notify_gift(bot: Bot, recipient_id: int, payer_name: str, diamonds: int) -> None:
    L = await texts_for_user(recipient_id)
    await _safe_send(bot, recipient_id, L.GIFT_RECEIVED.format(name=esc(payer_name), diamonds=diamonds))


async def _safe_send(bot: Bot, user_id: int, text: str) -> None:
    try:
        await bot.send_message(user_id, text)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
