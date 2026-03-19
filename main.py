import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import database as db
from config import BOT_TOKEN
from handlers import start, modules, shop, profile, help, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env file!")

    await db.init_db()
    logger.info("Database initialized.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register routers
    dp.include_router(start.router)
    dp.include_router(modules.router)
    dp.include_router(shop.router)
    dp.include_router(profile.router)
    dp.include_router(help.router)
    dp.include_router(admin.router)

    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
