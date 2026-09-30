"""🛠 Adminlar harakatlari jurnali: balans berish, to'lovni qaytarish, karta buyurtmasini ko'rib chiqish.
Har bir harakat admin_log ga yoziladi (/hisobot uchun); harakatni boshqa admin qilgan bo'lsa,
bot egasiga (OWNER_IDS) darhol xabar boradi."""
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import db
from config import OWNER_IDS
from economy import CURRENCY_EMOJI
from i18n import texts_for_user
from utils import esc


async def record(
    bot: Bot, admin, action: str, target_id: int | None = None, currency: str | None = None,
    amount: int = 0, note: str | None = None,
) -> None:
    """admin — aiogram User (harakatni qilgan kishi)."""
    await db.log_admin_action(admin.id, action, target_id, currency, amount, note)
    for owner_id in OWNER_IDS - {admin.id}:
        L = await texts_for_user(owner_id)
        target = await db.get_user(target_id) if target_id else None
        text = L.OWNER_ADMIN_ACTION.format(
            admin=esc(admin.full_name), admin_id=admin.id,
            action=L.ADMIN_ACTION_NAMES.get(action, action).format(
                amount=amount, emoji=CURRENCY_EMOJI.get(currency, ""), note=esc(note or ""),
            ),
            target=esc(target["full_name"]) if target else "—", target_id=target_id or "—",
        )
        try:
            await bot.send_message(owner_id, text)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
