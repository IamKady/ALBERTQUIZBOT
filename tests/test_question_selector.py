import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.models import Base, Question, Chat
from bot.poll_manager.question_selector import QuestionSelector

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def session_with_questions():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Insert 3 test questions
        q1 = Question(
            question_text="Q1", option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option=0, category="Science", difficulty="Easy"
        )
        q2 = Question(
            question_text="Q2", option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option=1, category="Science", difficulty="Medium"
        )
        session.add_all([q1, q2])
        await session.commit()

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_question_selector_non_repeating(session_with_questions):
    chat = Chat(chat_id=123, chat_title="Test", chat_type="group", is_active=True)
    session_with_questions.add(chat)
    await session_with_questions.commit()

    # Pick first question
    q_first = await QuestionSelector.get_next_question(session_with_questions, chat)
    assert q_first is not None

    # Pick second question
    q_second = await QuestionSelector.get_next_question(session_with_questions, chat)
    assert q_second is not None
    assert q_second.id != q_first.id

    # Third pick should reset cycle since all 2 questions were used
    q_third = await QuestionSelector.get_next_question(session_with_questions, chat)
    assert q_third is not None
