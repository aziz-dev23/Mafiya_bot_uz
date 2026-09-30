"""Tun va tongda guruhni setChatPermissions bilan yopish, kunduzi asl ruxsatlarni qaytarish.

Asl ruxsatlar bazada saqlanadi — bot o'yin o'rtasida qayta ishga tushsa, restore_all_locks()
ularni tiklaydi. Botda cheklash huquqi bo'lmasa, eski usul (xabarlarni o'chirish, chat_guard.py)
ishlayveradi va adminlarga bir marta ogohlantirish yuboriladi."""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatPermissions

import db
import texts

from .models import Game

logger = logging.getLogger(__name__)

LOCKED_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)

# Shu guruhlarga "cheklash huquqi yo'q" ogohlantirishi allaqachon yuborilgan.
_warned_chats: set[int] = set()


async def lock_chat(bot: Bot, game: Game) -> None:
    if game.chat_locked:
        return
    try:
        chat = await bot.get_chat(game.chat_id)
        original = chat.permissions or ChatPermissions(can_send_messages=True)
        await db.save_chat_lock(game.chat_id, original.model_dump_json(exclude_none=True))
        await bot.set_chat_permissions(game.chat_id, LOCKED_PERMISSIONS, use_independent_chat_permissions=True)
        game.chat_locked = True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.info("Guruh %s ni yopib bo'lmadi: %s", game.chat_id, e)
        await db.delete_chat_lock(game.chat_id)
        if game.chat_id not in _warned_chats:
            _warned_chats.add(game.chat_id)
            try:
                await bot.send_message(game.chat_id, texts.CHAT_LOCK_NO_RIGHTS)
            except (TelegramBadRequest, TelegramForbiddenError):
                pass


async def _restore(bot: Bot, chat_id: int, permissions_json: str) -> bool:
    try:
        permissions = ChatPermissions.model_validate_json(permissions_json)
        await bot.set_chat_permissions(chat_id, permissions, use_independent_chat_permissions=True)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning("Guruh %s ruxsatlarini tiklab bo'lmadi: %s", chat_id, e)
        return False
    return True


async def unlock_chat(bot: Bot, game: Game) -> None:
    saved = await db.get_chat_lock(game.chat_id)
    game.chat_locked = False
    if saved is None:
        return
    await _restore(bot, game.chat_id, saved)
    await db.delete_chat_lock(game.chat_id)


async def restore_all_locks(bot: Bot) -> None:
    """Bot ishga tushganda: tugamay qolgan o'yinlar tufayli yopiq qolgan guruhlarni ochadi."""
    for row in await db.all_chat_locks():
        await _restore(bot, row["chat_id"], row["permissions"])
        await db.delete_chat_lock(row["chat_id"])
