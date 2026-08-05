from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from aiogram.enums import ChatMemberStatus
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION, IS_MEMBER, ADMINISTRATOR
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import get_or_create_chat, update_chat
from bot.utils.logger import logger

router = Router()

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> ADMINISTRATOR))
async def bot_added_or_promoted(event: ChatMemberUpdated, session: AsyncSession, scheduler=None):
    chat = event.chat
    logger.info(f"Bot added/promoted in chat: {chat.title} ({chat.id})")
    
    db_chat = await get_or_create_chat(
        session=session,
        chat_id=chat.id,
        chat_title=chat.title,
        chat_type=chat.type
    )
    await update_chat(session, chat.id, is_active=True)

    # Automatically schedule quiz cycle immediately without any manual command
    if scheduler:
        scheduler.schedule_chat(chat.id, delay_seconds=5)
    
    try:
        await event.bot.send_message(
            chat_id=chat.id,
            text=f"🎉 **Albert Quiz Bot is now active in {chat.title or 'this group'}!**\n\nI will automatically send non-repeating quiz polls continuously at random intervals. Get ready to test your knowledge!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Could not send welcome message to chat {chat.id}: {e}")

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def bot_removed_from_group(event: ChatMemberUpdated, session: AsyncSession, scheduler=None):
    chat = event.chat
    logger.info(f"Bot removed from chat: {chat.title} ({chat.id})")
    await update_chat(session, chat.id, is_active=False)
    if scheduler:
        scheduler.unschedule_chat(chat.id)


