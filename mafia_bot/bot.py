import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import db
from config import BOT_TOKEN
from handlers import (
    admin,
    afterlife,
    chat_guard,
    common,
    day,
    group_settings,
    hero,
    items,
    lobby,
    market,
    menu,
    night,
    ranking,
    shop,
    transfer,
)
from autogame import auto_game_loop
from game.chatlock import restore_all_locks
from ratelimit import RateLimitMiddleware
from weekly import weekly_rewards_loop


async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylida BOT_TOKEN ni belgilang (.env.example ga qarang).")


    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # Barcha yuborish/tahrirlash so'rovlari Telegram limitlariga mos navbat orqali o'tadi.
    bot.session.middleware(RateLimitMiddleware())
    # Oldingi ishga tushishda tugamay qolgan o'yinlar tufayli yopiq qolgan guruhlarni ochamiz.
    await restore_all_locks(bot)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(menu.router)
    dp.include_router(shop.router)
    dp.include_router(market.router)
    dp.include_router(items.router)
    dp.include_router(hero.router)
    dp.include_router(ranking.router)
    dp.include_router(transfer.router)
    dp.include_router(admin.router)
    dp.include_router(lobby.router)
    dp.include_router(night.router)
    dp.include_router(day.router)
    dp.include_router(afterlife.router)
    dp.include_router(group_settings.router)
    # Oxirida: boshqa routerlar ushlamagan guruh xabarlarini tunda o'chiradi
    dp.include_router(chat_guard.router)

    await bot.set_my_commands(
        [
            BotCommand(command="mafia", description="Yangi Mafiya o'yini boshlash (guruhda)"),
            BotCommand(command="stop", description="Joriy o'yinni to'xtatish"),
            BotCommand(command="shop", description="Olmos sotib olish"),
            BotCommand(command="almashtir", description="Olmosni Dollarga almashtirish"),
            BotCommand(command="market", description="Bozor — valyutalar savdosi"),
            BotCommand(command="dokon", description="Buyumlar do'koni (Himoya, Miltiq va h.k.)"),
            BotCommand(command="sumka", description="Mening buyumlarim (yoqish/o'chirish)"),
            BotCommand(command="send", description="Boshqa foydalanuvchiga Dollar yuborish"),
            BotCommand(command="sendgem", description="Boshqa foydalanuvchiga Olmos yuborish"),
            BotCommand(command="profile", description="Profilingiz (balans, statistika)"),
            BotCommand(command="geroy", description="Geroyni sotib olish / darajasini oshirish"),
            BotCommand(command="top", description="Umumiy reyting (barcha o'yinlar)"),
            BotCommand(command="top1", description="Kunlik reyting"),
            BotCommand(command="top7", description="Haftalik reyting"),
            BotCommand(command="top30", description="Oylik reyting"),
            BotCommand(command="rollar", description="Barcha rollar tavsifi"),
            BotCommand(command="sozlamalar", description="Guruh sozlamalari (adminlar uchun)"),
            BotCommand(command="help", description="Yordam"),
        ]
    )

    weekly_task = asyncio.create_task(weekly_rewards_loop(bot))
    auto_task = asyncio.create_task(auto_game_loop(bot))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        weekly_task.cancel()
        auto_task.cancel()
        await db.close_db()


if __name__ == "__main__":
    asyncio.run(main())
