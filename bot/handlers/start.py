from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import get_or_create_user, get_or_create_chat, update_chat

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, i18n, scheduler=None):
    if message.from_user:
        await get_or_create_user(
            session=session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )

    if message.chat.type in ["group", "supergroup"]:
        chat = await get_or_create_chat(
            session=session,
            chat_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type
        )
        await update_chat(session, message.chat.id, is_active=True)
        if scheduler:
            scheduler.schedule_chat(message.chat.id, delay_seconds=5)

    await message.answer(i18n("welcome"), parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: Message, i18n):
    await message.answer(i18n("help"), parse_mode="Markdown")

