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
    bonus_vip,
    cosmetics_shop,
    chat_guard,
    common,
    day,
    gifts,
    group_premium,
    group_settings,
    hero,
    items,
    lobby,
    market,
    menu,
    night,
    ranking,
    report,
    season_pass,
    shop,
    stars,
    transfer,
)
from autogame import auto_game_loop
from game.chatlock import restore_all_locks
from group_features import group_features_loop
from i18n import RU, UZ, LanguageMiddleware, get_texts
from ratelimit import RateLimitMiddleware
from season import season_reminder_loop
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
    # Har bir handlerga L (chat tili) va UL (foydalanuvchi tili) matnlarini beradi.
    dp.update.outer_middleware(LanguageMiddleware())

    dp.include_router(common.router)
    dp.include_router(menu.router)
    dp.include_router(shop.router)
    dp.include_router(stars.router)
    dp.include_router(market.router)
    dp.include_router(items.router)
    dp.include_router(hero.router)
    dp.include_router(cosmetics_shop.router)
    dp.include_router(bonus_vip.router)
    dp.include_router(season_pass.router)
    dp.include_router(ranking.router)
    dp.include_router(transfer.router)
    dp.include_router(gifts.router)
    dp.include_router(group_premium.router)
    dp.include_router(admin.router)
    dp.include_router(report.router)
    dp.include_router(lobby.router)
    dp.include_router(night.router)
    dp.include_router(day.router)
    dp.include_router(afterlife.router)
    dp.include_router(group_settings.router)
    # Oxirida: boshqa routerlar ushlamagan guruh xabarlarini tunda o'chiradi
    dp.include_router(chat_guard.router)

    # Standart (o'zbekcha) va ruscha Telegram ilovasi uchun buyruqlar tavsifi.
    for code, language_code in ((UZ, None), (RU, "ru")):
        commands = [BotCommand(command=c, description=d) for c, d in get_texts(code).BOT_COMMANDS.items()]
        await bot.set_my_commands(commands, language_code=language_code)

    weekly_task = asyncio.create_task(weekly_rewards_loop(bot))
    auto_task = asyncio.create_task(auto_game_loop(bot))
    season_task = asyncio.create_task(season_reminder_loop(bot))
    group_task = asyncio.create_task(group_features_loop(bot))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        weekly_task.cancel()
        auto_task.cancel()
        season_task.cancel()
        group_task.cancel()
        await db.close_db()


if __name__ == "__main__":
    asyncio.run(main())
