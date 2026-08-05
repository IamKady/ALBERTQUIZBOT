import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.models import Base, Question, Chat, User
from bot.database.crud import (
    get_or_create_chat,
    get_or_create_user,
    record_user_answer,
    update_chat
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_get_or_create_chat(test_session):
    chat = await get_or_create_chat(test_session, chat_id=-100123456789, chat_title="Test Group", chat_type="supergroup")
    assert chat.chat_id == -100123456789
    assert chat.chat_title == "Test Group"
    assert chat.is_active is True

@pytest.mark.asyncio
async def test_record_user_answer(test_session):
    user = await get_or_create_user(test_session, user_id=999, username="testuser", first_name="Test")
    assert user.user_id == 999

    pts, score_obj = await record_user_answer(test_session, user_id=999, chat_id=-100123456789, is_correct=True, is_fastest=True)
    assert pts == 7  # 5 correct + 2 fastest bonus
    assert score_obj.score == 7
    assert score_obj.correct_count == 1
    assert score_obj.fastest_bonus_count == 1

    pts2, score_obj2 = await record_user_answer(test_session, user_id=999, chat_id=-100123456789, is_correct=False)
    assert pts2 == 0
    assert score_obj2.score == 7
    assert score_obj2.wrong_count == 1
