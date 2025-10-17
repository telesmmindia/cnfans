import asyncio
import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import bot
from database import db
from handlers import get_handlers_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(get_handlers_router())


async def on_startup():
    logger.info("Bot starting...")
    await db.create_tables()
    logger.info("Database initialized")

async def on_shutdown():
    logger.info("Bot shutting down...")
    if db.connection:
        db.connection.close()

async def main():
    await on_startup()
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())
