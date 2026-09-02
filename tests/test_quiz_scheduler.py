import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.models import Base, Chat, Question, ActivePoll
from bot.database.crud import (
    get_or_create_chat,
    create_active_poll,
    get_expired_active_polls,
    get_active_chat_polls,
    update_chat
)
from bot.scheduler.quiz_scheduler import cleanup_expired_polls, run_cron_cycle

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def scheduler_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_get_expired_active_polls_naive_utc(scheduler_session):
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    past_time = now_naive - timedelta(minutes=5)
    future_time = now_naive + timedelta(minutes=10)

    await create_active_poll(
        session=scheduler_session,
        poll_id="poll_expired_1",
        chat_id=-100111222,
        message_id=101,
        question_id=1,
        expires_at=past_time
    )

    await create_active_poll(
        session=scheduler_session,
        poll_id="poll_active_2",
        chat_id=-100111222,
        message_id=102,
        question_id=2,
        expires_at=future_time
    )

    expired = await get_expired_active_polls(scheduler_session)
    assert len(expired) == 1
    assert expired[0].poll_id == "poll_expired_1"

@pytest.mark.asyncio
async def test_chat_default_interval(scheduler_session):
    chat = await get_or_create_chat(
        session=scheduler_session,
        chat_id=-100999888,
        chat_title="10m Group",
        chat_type="supergroup"
    )
    assert chat.min_interval_mins == 10
    assert chat.max_interval_mins == 10
    assert chat.quiz_duration_mins == 10

@pytest.mark.asyncio
async def test_run_cron_cycle_dispatches_due_quiz(scheduler_session):
    mock_bot = MagicMock()
    mock_bot.stop_poll = AsyncMock()
    mock_bot.delete_message = AsyncMock()

    # Create active chat in DB
    chat = await get_or_create_chat(
        session=scheduler_session,
        chat_id=-100555666,
        chat_title="Cron Test Chat",
        chat_type="supergroup"
    )

    @asynccontextmanager
    async def mock_async_session():
        yield scheduler_session

    with patch("bot.scheduler.quiz_scheduler.async_session", side_effect=mock_async_session), \
         patch("bot.poll_manager.engine.PollManager.send_quiz_poll", new_callable=AsyncMock) as mock_send:
        mock_poll = MagicMock()
        mock_poll.poll_id = "poll_123"
        mock_send.return_value = mock_poll

        result = await run_cron_cycle(mock_bot)
        assert result["status"] == "success"
        assert result["quizzes_sent"] == 1
        assert result["total_active_chats"] == 1
