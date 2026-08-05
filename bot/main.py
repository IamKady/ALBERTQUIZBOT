import asyncio
import sys
from pathlib import Path

# Add project root directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from bot.config.settings import settings
from bot.database.session import init_db, async_session
from bot.handlers import main_router
from bot.middlewares import DbSessionMiddleware, I18nMiddleware, RateLimitMiddleware
from bot.scheduler import QuizScheduler
from bot.utils.logger import setup_logger, logger
from tools.seed_questions import seed_database

async def main():
    setup_logger()
    logger.info("Starting Albert Quiz Bot...")

    if not settings.BOT_TOKEN:
        logger.critical("BOT_TOKEN is not configured in environment or .env file!")
        sys.exit(1)

    # Initialize Database
    await init_db()

    # Seed dataset if database is empty
    await seed_database(50000)

    # Initialize Bot & Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Initialize Scheduler
    scheduler = QuizScheduler(bot)
    scheduler.start()

    # Inject dependencies into dispatcher workflow
    dp["scheduler"] = scheduler

    # Register Middlewares
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(I18nMiddleware())
    dp.message.middleware(RateLimitMiddleware(limit_seconds=1.0))

    # Register Router Handlers
    dp.include_router(main_router)

    # Initialize scheduling for existing active chats
    await scheduler.initialize_all_active_chats()

    logger.info("Albert Quiz Bot successfully launched and listening for updates...")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.stop()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution terminated.")
