from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import get_or_create_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, i18n):
    if message.from_user:
        await get_or_create_user(
            session=session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
    await message.answer(i18n("welcome"), parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: Message, i18n):
    await message.answer(i18n("help"), parse_mode="Markdown")
