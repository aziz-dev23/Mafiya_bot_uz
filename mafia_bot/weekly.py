import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import db
import texts
from economy import WEEKLY_REWARD_DIAMONDS

logger = logging.getLogger(__name__)

WEEK_SECONDS = 7 * 24 * 3600


async def pay_last_week(bot: Bot) -> bool:
    """O'tgan haftaning (dushanba 00:00 — yakshanba 23:59, Toshkent) /top7 top-3 ga olmos beradi.
    Hafta uchun mukofot bazada belgilanadi — bot qayta ishga tushsa ham ikki marta berilmaydi."""
    this_week = db.period_starts()["weekly"]
    last_week = this_week - WEEK_SECONDS
    rows = await db.top_points(since=last_week, until=this_week, limit=len(WEEKLY_REWARD_DIAMONDS))
    awards = [(row["user_id"], WEEKLY_REWARD_DIAMONDS[i]) for i, row in enumerate(rows)]
    if not await db.pay_weekly_rewards(last_week, awards):
        return False

    for place, (row, (user_id, diamonds)) in enumerate(zip(rows, awards), 1):
        try:
            await bot.send_message(
                user_id, texts.WEEKLY_REWARD_MESSAGE.format(place=place, points=row["total"], diamonds=diamonds)
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
    logger.info("Haftalik mukofot berildi (hafta boshi %s): %s", last_week, awards)
    return True


async def weekly_rewards_loop(bot: Bot) -> None:
    while True:
        try:
            await pay_last_week(bot)
        except Exception:
            logger.exception("Haftalik mukofotni berishda xatolik")
        next_week = db.period_starts()["weekly"] + WEEK_SECONDS
        await asyncio.sleep(max(1, next_week - time.time()) + 5)
