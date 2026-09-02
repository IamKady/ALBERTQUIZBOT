import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.config.settings import settings
from bot.models import Base
from bot.utils.logger import logger

# Engine connection parameters optimized for both local SQLite and serverless cloud PostgreSQL
engine_kwargs = {
    "echo": False,
    "future": True,
}

if settings.ASYNC_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Serverless cloud postgres connection resiliency
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    **engine_kwargs
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

from sqlalchemy import text

async def init_db():
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            # Automatically migrate legacy intervals (15 min min / 120 min max) or NULL intervals to standard 10 minutes
            await conn.execute(text(
                "UPDATE chats SET min_interval_mins = 10, max_interval_mins = 10 "
                "WHERE (min_interval_mins = 15 AND max_interval_mins = 120) "
                "OR min_interval_mins IS NULL OR max_interval_mins IS NULL"
            ))
        except Exception as e:
            logger.debug(f"Chat interval migration notice: {e}")
    logger.info("Database tables initialized successfully.")

async def get_db():
    async with async_session() as session:
        yield session
