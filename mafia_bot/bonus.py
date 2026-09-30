"""🎁 Kunlik bonus: kuniga bir marta (Toshkent kuni), ketma-ket kunlar bo'yicha oshib boradi."""
from datetime import datetime, timedelta, timezone

import db
from config import TIMEZONE_OFFSET_HOURS
from economy import (
    DAILY_BONUS_DAYS,
    DAILY_BONUS_FIRST,
    DAILY_BONUS_LAST_DAY_DIAMONDS,
    DAILY_BONUS_STEP,
    VIP_DAILY_BONUS_MULTIPLIER,
)

TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))


def bonus_for_day(day: int) -> tuple[int, int]:
    """(dollar, olmos) — ketma-ketlikning day-kuni uchun (VIP ko'paytmasisiz)."""
    dollars = DAILY_BONUS_FIRST + (day - 1) * DAILY_BONUS_STEP
    diamonds = DAILY_BONUS_LAST_DAY_DIAMONDS if day == DAILY_BONUS_DAYS else 0
    return dollars, diamonds


async def claim(user_id: int, now: datetime | None = None) -> dict:
    """Bugungi bonusni beradi. {"ok": bool, "day": N, "dollars": .., "diamonds": .., "vip": bool}."""
    now = now or datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    state = await db.daily_bonus_state(user_id)
    if state and state["last_day"] == today:
        return {"ok": False, "day": state["streak"]}
    # Kun o'tkazib yuborilsa yoki oxirgi kundan keyin — hisob yana 1-kundan.
    if state and state["last_day"] == yesterday and state["streak"] < DAILY_BONUS_DAYS:
        day = state["streak"] + 1
    else:
        day = 1
    dollars, diamonds = bonus_for_day(day)
    vip = await db.is_vip(user_id)
    if vip:
        dollars *= VIP_DAILY_BONUS_MULTIPLIER
    if not await db.claim_daily_bonus(user_id, today, day, dollars, diamonds):
        return {"ok": False, "day": day}
    return {"ok": True, "day": day, "dollars": dollars, "diamonds": diamonds, "vip": vip}
