import asyncio
import logging
from aiogram import Dispatcher, Bot, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from database import Database
from handlers import start, menu, modules, shop, profile, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация роутеров
dp.include_router(start.router)
dp.include_router(menu.router)
dp.include_router(modules.router)
dp.include_router(shop.router)
dp.include_router(profile.router)
dp.include_router(admin.router)

async def main():
    try:
        await db.init_db()
        logger.info("База данных инициализирована")
        logger.info("Бот запущен")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
