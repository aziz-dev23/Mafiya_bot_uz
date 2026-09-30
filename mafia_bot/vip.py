"""👑 VIP: 30 kunlik Telegram Stars obunasi. Telegram har 30 kunda avtomatik yangilaydi;
foydalanuvchi obunani Telegram'ning o'zida bekor qiladi — shunda muddat tugagach VIP o'chadi."""
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import db
from economy import ITEMS, VIP_PERIOD_SECONDS, VIP_WEEKLY_ITEM
from i18n import texts_for_user

logger = logging.getLogger(__name__)

PAYLOAD_PREFIX = "vip"


def build_payload(user_id: int) -> str:
    return f"{PAYLOAD_PREFIX}:{user_id}"


def parse_payload(payload: str) -> int | None:
    parts = payload.split(":")
    if len(parts) == 2 and parts[0] == PAYLOAD_PREFIX and parts[1].isdigit():
        return int(parts[1])
    return None


async def activate(user_id: int, charge_id: str, expiration: int | None) -> int:
    """To'lov (birinchi yoki navbatdagi) kelganda VIP muddatini belgilaydi va uni qaytaradi."""
    until = expiration or int(time.time()) + VIP_PERIOD_SECONDS
    await db.set_vip_until(user_id, max(until, await db.vip_until(user_id)), charge_id)
    return until


async def revoke(user_id: int) -> None:
    """Pul qaytarilganda VIP darhol o'chadi."""
    await db.set_vip_until(user_id, int(time.time()), None)


async def give_weekly_items(bot: Bot, week_start: int) -> int:
    """Har dushanba barcha faol VIP'larga bepul buyum (bir hafta uchun bir marta)."""
    key, count = VIP_WEEKLY_ITEM
    given = 0
    for user_id in await db.active_vip_users():
        if not await db.mark_vip_weekly_item(user_id, week_start):
            continue
        await db.add_item(user_id, key, count)
        given += 1
        L = await texts_for_user(user_id)
        try:
            await bot.send_message(
                user_id, L.VIP_WEEKLY_GIFT.format(count=count, emoji=ITEMS[key]["emoji"], name=L.ITEM_NAMES[key])
            )
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    return given
