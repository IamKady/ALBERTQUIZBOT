import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.models import Base, User, UserScore
from bot.leaderboard.service import LeaderboardService

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def session_with_scores():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        u1 = User(user_id=101, username="alice", first_name="Alice")
        u2 = User(user_id=102, username="bob", first_name="Bob")
        session.add_all([u1, u2])

        s1 = UserScore(user_id=101, chat_id=500, score=25, correct_count=5, wrong_count=1, fastest_bonus_count=2)
        s2 = UserScore(user_id=102, chat_id=500, score=15, correct_count=3, wrong_count=2, fastest_bonus_count=0)
        session.add_all([s1, s2])
        await session.commit()

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_leaderboard_service(session_with_scores):
    top = await LeaderboardService.get_top_users(session_with_scores, chat_id=500, period="all_time", limit=10)
    assert len(top) == 2
    assert top[0]["user_id"] == 101
    assert top[0]["score"] == 25
    assert top[0]["rank"] == 1
    assert top[1]["user_id"] == 102
    assert top[1]["score"] == 15
    assert top[1]["rank"] == 2

    alice_stats = await LeaderboardService.get_user_score_and_rank(session_with_scores, user_id=101, chat_id=500)
    assert alice_stats["score"] == 25
    assert alice_stats["rank"] == 1
    assert alice_stats["accuracy"] == 83.3
