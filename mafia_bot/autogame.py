"""Avtomatik o'yin: guruh sozlamasidagi vaqtda (Toshkent) har kuni ro'yxat o'zi ochiladi."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot

import db
from config import TIMEZONE_OFFSET_HOURS
from game.manager import manager
from game.settings import GroupSettings
from i18n import get_texts

logger = logging.getLogger(__name__)

_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))
CHECK_INTERVAL = 20
# (chat_id, sana) — bir kunda bir guruhda ikki marta ochilmasligi uchun.
_opened: set[tuple[int, str]] = set()


async def open_due_lobbies(bot: Bot, now: datetime | None = None) -> list[int]:
    from handlers.lobby import open_lobby

    now = now or datetime.now(_TZ)
    hhmm, today = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
    opened = []
    for row in await db.all_group_settings():
        settings = GroupSettings.from_json(row["settings"])
        chat_id = row["chat_id"]
        if settings.auto_time != hhmm or (chat_id, today) in _opened or manager.get_game(chat_id):
            continue
        _opened.add((chat_id, today))
        try:
            await bot.send_message(chat_id, get_texts(settings.lang).AUTO_GAME_OPENED)
            if await open_lobby(bot, chat_id):
                opened.append(chat_id)
        except Exception:
            logger.exception("Guruh %s da avtomatik o'yinni ochib bo'lmadi", chat_id)
    return opened


async def auto_game_loop(bot: Bot) -> None:
    while True:
        try:
            await open_due_lobbies(bot)
        except Exception:
            logger.exception("Avtomatik o'yin tekshiruvida xatolik")
        await asyncio.sleep(CHECK_INTERVAL)
