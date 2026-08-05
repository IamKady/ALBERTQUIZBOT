from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config.settings import settings
from bot.database.crud import get_chat, update_chat, get_active_chats, get_global_stats
from bot.utils.backup import backup_database
from bot.utils.exporter import export_questions_to_json
from bot.utils.logger import logger

router = Router()

def is_admin(user_id: int) -> bool:
    return settings.is_admin(user_id)

def get_admin_menu_keyboard(chat_id: int, is_active: bool, mixed_mode: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Pause Quizzes" if is_active else "🟢 Resume Quizzes"
    mixed_text = "🔀 Mixed Mode: ON" if mixed_mode else "🔀 Mixed Mode: OFF"

    keyboard = [
        [
            InlineKeyboardButton(text=toggle_text, callback_query_data=f"adm_toggle_{chat_id}"),
            InlineKeyboardButton(text=mixed_text, callback_query_data=f"adm_mixed_{chat_id}")
        ],
        [
            InlineKeyboardButton(text="⏱️ Set 10m Interval", callback_query_data=f"adm_interval_10_{chat_id}"),
            InlineKeyboardButton(text="⏱️ Set 30m Min Interval", callback_query_data=f"adm_interval_30_{chat_id}")
        ],
        [
            InlineKeyboardButton(text="⏳ Set 10m Quiz Duration", callback_query_data=f"adm_dur_10_{chat_id}"),
            InlineKeyboardButton(text="⏳ Set 5m Quiz Duration", callback_query_data=f"adm_dur_5_{chat_id}")
        ],
        [
            InlineKeyboardButton(text="📊 Stats", callback_query_data="adm_stats"),
            InlineKeyboardButton(text="💾 DB Backup", callback_query_data="adm_backup")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id) and message.chat.type not in ["group", "supergroup"]:
        await message.answer("⚠️ Admin access restricted.")
        return

    chat = await get_chat(session, message.chat.id)
    is_active = chat.is_active if chat else True
    mixed_mode = chat.mixed_mode if chat else True

    text = (
        f"⚙️ **Admin Control Panel**\n\n"
        f"📍 **Target Chat ID:** `{message.chat.id}`\n"
        f"🔄 **Quiz Status:** {'Active 🟢' if is_active else 'Paused 🔴'}\n"
        f"⏱️ **Min Interval:** {chat.min_interval_mins if chat else 15} mins\n"
        f"⏱️ **Max Interval:** {chat.max_interval_mins if chat else 120} mins\n"
        f"⏳ **Quiz Duration:** {chat.quiz_duration_mins if chat else 10} mins\n"
        f"🔀 **Mixed Category Mode:** {'Enabled' if mixed_mode else 'Disabled'}\n"
    )
    await message.answer(text, reply_markup=get_admin_menu_keyboard(message.chat.id, is_active, mixed_mode), parse_mode="Markdown")

@router.callback_query(F.data.startswith("adm_toggle_"))
async def cb_toggle_chat(callback: CallbackQuery, session: AsyncSession, scheduler):
    chat_id = int(callback.data.split("_")[-1])
    chat = await get_chat(session, chat_id)
    if not chat:
        await callback.answer("Chat not found.")
        return

    new_status = not chat.is_active
    await update_chat(session, chat_id, is_active=new_status)
    if new_status:
        scheduler.schedule_chat(chat_id, delay_seconds=10)
    else:
        scheduler.unschedule_chat(chat_id)

    await callback.message.edit_reply_markup(
        reply_markup=get_admin_menu_keyboard(chat_id, new_status, chat.mixed_mode)
    )
    await callback.answer(f"Quiz status updated to {'Active' if new_status else 'Paused'}.")

@router.callback_query(F.data.startswith("adm_mixed_"))
async def cb_toggle_mixed(callback: CallbackQuery, session: AsyncSession):
    chat_id = int(callback.data.split("_")[-1])
    chat = await get_chat(session, chat_id)
    if not chat:
        await callback.answer("Chat not found.")
        return

    new_mixed = not chat.mixed_mode
    await update_chat(session, chat_id, mixed_mode=new_mixed)

    await callback.message.edit_reply_markup(
        reply_markup=get_admin_menu_keyboard(chat_id, chat.is_active, new_mixed)
    )
    await callback.answer(f"Mixed mode updated to {'ON' if new_mixed else 'OFF'}.")

@router.callback_query(F.data.startswith("adm_interval_"))
async def cb_set_interval(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    mins = int(parts[2])
    chat_id = int(parts[3])
    await update_chat(session, chat_id, min_interval_mins=mins)
    await callback.answer(f"Minimum interval set to {mins} minutes.")

@router.callback_query(F.data.startswith("adm_dur_"))
async def cb_set_duration(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    dur = int(parts[2])
    chat_id = int(parts[3])
    await update_chat(session, chat_id, quiz_duration_mins=dur)
    await callback.answer(f"Quiz duration set to {dur} minutes.")

@router.callback_query(F.data == "adm_stats")
async def cb_admin_stats(callback: CallbackQuery, session: AsyncSession):
    stats = await get_global_stats(session)
    text = (
        f"📊 **Global System Stats**\n\n"
        f"• Total Questions: {stats['total_questions']:,}\n"
        f"• Total Active Chats: {stats['total_chats']:,}\n"
        f"• Total Registered Users: {stats['total_users']:,}\n"
        f"• Total Quizzes Sent: {stats['total_polls_sent']:,}\n"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "adm_backup")
async def cb_admin_backup(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Unauthorized.", show_alert=True)
        return
    backup_path = await backup_database()
    await callback.message.answer(f"💾 **Database Backup Created:**\n`{backup_path}`", parse_mode="Markdown")
    await callback.answer()

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, session: AsyncSession, bot):
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ Admin only.")
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Usage: `/broadcast Your message here`", parse_mode="Markdown")
        return

    chats = await get_active_chats(session)
    sent_count = 0
    for chat in chats:
        try:
            await bot.send_message(chat_id=chat.chat_id, text=f"📢 **Announcement:**\n\n{text}", parse_mode="Markdown")
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to {chat.chat_id}: {e}")

    await message.answer(f"✅ Announcement broadcasted to {sent_count} active chats.")
