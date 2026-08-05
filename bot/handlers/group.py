from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, ADMINISTRATOR
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import get_or_create_chat, update_chat
from bot.utils.logger import logger

router = Router()

@router.my_chat_member(
    ChatMemberUpdatedFilter(
        member_status_changed=IS_MEMBER >> ADMINISTRATOR
    )
)
async def bot_promoted_to_admin(event: ChatMemberUpdated, session: AsyncSession, scheduler):
    chat = event.chat
    logger.info(f"Bot promoted to admin in chat: {chat.title} ({chat.id})")
    
    db_chat = await get_or_create_chat(
        session=session,
        chat_id=chat.id,
        chat_title=chat.title,
        chat_type=chat.type
    )
    await update_chat(session, chat.id, is_active=True)

    # Automatically schedule quiz cycle immediately without any manual command
    scheduler.schedule_chat(chat.id, delay_seconds=5)
    
    try:
        await event.bot.send_message(
            chat_id=chat.id,
            text=f"🎉 **Albert Quiz Bot is now active in {chat.title}!**\n\nI will automatically send non-repeating quiz polls continuously at random intervals. Get ready to test your knowledge!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Could not send welcome message to chat {chat.id}: {e}")

@router.my_chat_member(
    ChatMemberUpdatedFilter(
        member_status_changed=ADMINISTRATOR >> IS_MEMBER
    )
)
async def bot_demoted_from_admin(event: ChatMemberUpdated, session: AsyncSession, scheduler):
    chat = event.chat
    logger.info(f"Bot demoted from admin in chat: {chat.title} ({chat.id})")
    await update_chat(session, chat.id, is_active=False)
    scheduler.unschedule_chat(chat.id)
