import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.config.settings import settings
from bot.models import Base
from bot.utils.logger import logger

# SQLite needs connect_args check_same_thread=False
connect_args = {}
if settings.ASYNC_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    future=True
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")

async def get_db():
    async with async_session() as session:
        yield session
