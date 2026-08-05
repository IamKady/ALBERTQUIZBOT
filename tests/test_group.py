import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Chat, ChatMemberUpdated, User, ChatMemberOwner, ChatMemberMember, ChatMemberLeft
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.models import Base, Chat as ChatModel
from bot.handlers.group import bot_added_or_promoted, bot_removed_from_group
from bot.handlers.start import cmd_start
from bot.handlers.admin import cmd_admin, is_user_chat_admin

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
async def test_bot_added_or_promoted(test_session):
    chat = Chat(id=-100999, title="Test Group", type="supergroup")
    user = User(id=1, is_bot=False, first_name="Admin")
    bot_user = User(id=2, is_bot=True, first_name="AlbertBot")
    
    event = MagicMock(spec=ChatMemberUpdated)
    event.chat = chat
    event.from_user = user
    event.new_chat_member = ChatMemberMember(user=bot_user)
    event.bot = AsyncMock()

    scheduler = MagicMock()

    await bot_added_or_promoted(event, test_session, scheduler)

    scheduler.schedule_chat.assert_called_once_with(-100999, delay_seconds=5)
    event.bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_cmd_start_in_group(test_session):
    message = AsyncMock()
    message.chat = Chat(id=-100888, title="New Group", type="group")
    message.from_user = User(id=10, is_bot=False, first_name="Alice")

    i18n = lambda key, **kw: "Welcome!"
    scheduler = MagicMock()

    await cmd_start(message, test_session, i18n, scheduler)

    scheduler.schedule_chat.assert_called_once_with(-100888, delay_seconds=5)
    message.answer.assert_called_once_with("Welcome!", parse_mode="Markdown")

@pytest.mark.asyncio
async def test_is_user_chat_admin_permission():
    bot = AsyncMock()
    
    # Creator/Admin user
    bot.get_chat_member.return_value = MagicMock(status="administrator")
    res1 = await is_user_chat_admin(bot, -100123, 100)
    assert res1 is True

    # Regular member user
    bot.get_chat_member.return_value = MagicMock(status="member")
    res2 = await is_user_chat_admin(bot, -100123, 200)
    assert res2 is False
