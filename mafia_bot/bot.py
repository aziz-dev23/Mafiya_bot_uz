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
from handlers import admin, common, day, hero, items, lobby, market, menu, night, ranking, shop, transfer


async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylida BOT_TOKEN ni belgilang (.env.example ga qarang).")

    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
            BotCommand(command="help", description="Yordam"),
        ]
    )

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await db.close_db()


if __name__ == "__main__":
    asyncio.run(main())
