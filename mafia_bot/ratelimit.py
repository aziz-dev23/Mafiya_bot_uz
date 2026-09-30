"""Telegram limitlari uchun navbat: barcha yuborish/tahrirlash so'rovlari shu yerdan o'tadi.

Limitlar (config.py): bitta chatga soniyasiga 1 ta, guruhga daqiqasiga 20 ta, jami soniyasiga ~25 ta.
429 (Too Many Requests) kelsa, retry_after soniya kutib qayta yuboriladi.
"""
import asyncio
import logging
import time
from collections import deque

from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import (
    CopyMessage,
    EditMessageCaption,
    EditMessageReplyMarkup,
    EditMessageText,
    ForwardMessage,
    SendDocument,
    SendMessage,
    SendInvoice,
    SendPhoto,
    TelegramMethod,
)
from aiogram.methods.base import Response, TelegramType

from config import (
    RATE_GLOBAL_PER_SECOND,
    RATE_GROUP_PER_MINUTE,
    RATE_PER_CHAT_INTERVAL,
    RATE_RETRY_ATTEMPTS,
)

logger = logging.getLogger(__name__)

THROTTLED_METHODS = (
    SendMessage,
    SendPhoto,
    SendDocument,
    SendInvoice,
    EditMessageText,
    EditMessageReplyMarkup,
    EditMessageCaption,
    CopyMessage,
    ForwardMessage,
)


class RateLimiter:
    def __init__(
        self,
        per_chat_interval: float = RATE_PER_CHAT_INTERVAL,
        group_per_minute: int = RATE_GROUP_PER_MINUTE,
        global_per_second: int = RATE_GLOBAL_PER_SECOND,
    ) -> None:
        self.per_chat_interval = per_chat_interval
        self.group_per_minute = group_per_minute
        self.global_per_second = global_per_second
        self._chat_locks: dict[int, asyncio.Lock] = {}
        self._chat_last: dict[int, float] = {}
        self._group_window: dict[int, deque[float]] = {}
        self._global_window: deque[float] = deque()

    def _delay(self, chat_id: int, now: float) -> float:
        wait = self._chat_last.get(chat_id, 0.0) + self.per_chat_interval - now

        while self._global_window and self._global_window[0] <= now - 1:
            self._global_window.popleft()
        if len(self._global_window) >= self.global_per_second:
            wait = max(wait, self._global_window[0] + 1 - now)

        if chat_id < 0:
            window = self._group_window.setdefault(chat_id, deque())
            while window and window[0] <= now - 60:
                window.popleft()
            if len(window) >= self.group_per_minute:
                wait = max(wait, window[0] + 60 - now)
        return wait

    def _record(self, chat_id: int, now: float) -> None:
        self._chat_last[chat_id] = now
        self._global_window.append(now)
        if chat_id < 0:
            self._group_window.setdefault(chat_id, deque()).append(now)

    async def acquire(self, chat_id: int) -> None:
        """Bitta chat uchun so'rovlar navbat bilan (yuborilish tartibida) o'tadi."""
        lock = self._chat_locks.setdefault(chat_id, asyncio.Lock())
        async with lock:
            while True:
                now = time.monotonic()
                wait = self._delay(chat_id, now)
                if wait <= 0:
                    # Tekshiruv va yozish orasida await yo'q — boshqa korutinlar aralasha olmaydi.
                    self._record(chat_id, now)
                    return
                await asyncio.sleep(wait)


class RateLimitMiddleware(BaseRequestMiddleware):
    def __init__(self, limiter: RateLimiter | None = None) -> None:
        self.limiter = limiter or RateLimiter()

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        chat_id = getattr(method, "chat_id", None)
        throttled = isinstance(method, THROTTLED_METHODS) and isinstance(chat_id, int)
        attempt = 0
        while True:
            if throttled:
                await self.limiter.acquire(chat_id)
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as e:
                attempt += 1
                if attempt > RATE_RETRY_ATTEMPTS:
                    raise
                logger.warning("429: %s so'rovi %s soniyadan keyin qayta yuboriladi", type(method).__name__, e.retry_after)
                await asyncio.sleep(e.retry_after)
