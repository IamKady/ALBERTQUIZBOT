from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import get_global_stats, get_chat, get_or_create_chat, get_or_create_user
from bot.leaderboard.service import LeaderboardService
from bot.poll_manager.engine import PollManager
from bot.models import Question

router = Router()

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    stats = await get_global_stats(session)
    text = (
        f"📊 **Albert Quiz Bot Statistics**\n\n"
        f"📚 **Total Questions in Database:** {stats['total_questions']:,}\n"
        f"👥 **Total Registered Users:** {stats['total_users']:,}\n"
        f"💬 **Active Groups/Channels:** {stats['total_chats']:,}\n"
        f"🎯 **Total Quizzes Sent:** {stats['total_polls_sent']:,}\n"
        f"✅ **Correct Answers:** {stats['correct_answers']:,}\n"
        f"❌ **Wrong Answers:** {stats['wrong_answers']:,}\n"
        f"📈 **Overall Participation Accuracy:** {stats['participation_pct']}%\n"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("categories"))
async def cmd_categories(message: Message, session: AsyncSession):
    stmt = select(Question.category, func.count(Question.id)).group_by(Question.category)
    res = await session.execute(stmt)
    categories = res.all()

    if not categories:
        await message.answer("📚 No categories found in database.")
        return

    text = "📚 **Available Quiz Categories:**\n\n"
    for cat, count in categories:
        text += f"• **{cat}**: {count:,} questions\n"

    await message.answer(text, parse_mode="Markdown")

def build_leaderboard_keyboard(period: str = "all_time") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📅 Daily" if period == "daily" else "Daily", callback_query_data="lb_daily"),
            InlineKeyboardButton(text="🗓️ Weekly" if period == "weekly" else "Weekly", callback_query_data="lb_weekly"),
            InlineKeyboardButton(text="📆 Monthly" if period == "monthly" else "Monthly", callback_query_data="lb_monthly"),
            InlineKeyboardButton(text="🏆 All-Time" if period == "all_time" else "All-Time", callback_query_data="lb_all_time"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message, session: AsyncSession):
    chat_id = message.chat.id if message.chat.type in ["group", "supergroup"] else None
    top_users = await LeaderboardService.get_top_users(session, chat_id=chat_id, period="all_time", limit=10)

    title = "🏆 **Global Leaderboard (All-Time)**" if not chat_id else f"🏆 **Group Leaderboard (All-Time)**"
    text = f"{title}\n\n"

    if not top_users:
        text += "No participants yet. Be the first to answer a quiz question!"
    else:
        for u in top_users:
            medal = "🥇" if u["rank"] == 1 else "🥈" if u["rank"] == 2 else "🥉" if u["rank"] == 3 else f"{u['rank']}."
            text += f"{medal} **{u['name']}** — **{u['score']} pts** (✅ {u['correct']} | ⚡ {u['fastest']})\n"

    await message.answer(text, reply_markup=build_leaderboard_keyboard("all_time"), parse_mode="Markdown")

@router.callback_query(F.data.startswith("lb_"))
async def cb_leaderboard_switch(callback: CallbackQuery, session: AsyncSession):
    period = callback.data.replace("lb_", "")
    chat_id = callback.message.chat.id if callback.message.chat.type in ["group", "supergroup"] else None
    top_users = await LeaderboardService.get_top_users(session, chat_id=chat_id, period=period, limit=10)

    period_title = period.replace("_", " ").title()
    text = f"🏆 **Leaderboard ({period_title})**\n\n"

    if not top_users:
        text += "No records found for this timeframe."
    else:
        for u in top_users:
            medal = "🥇" if u["rank"] == 1 else "🥈" if u["rank"] == 2 else "🥉" if u["rank"] == 3 else f"{u['rank']}."
            text += f"{medal} **{u['name']}** — **{u['score']} pts** (✅ {u['correct']} | ⚡ {u['fastest']})\n"

    await callback.message.edit_text(text, reply_markup=build_leaderboard_keyboard(period), parse_mode="Markdown")
    await callback.answer()

@router.message(Command("myscore"))
async def cmd_myscore(message: Message, session: AsyncSession):
    user_id = message.from_user.id
    chat_id = message.chat.id if message.chat.type in ["group", "supergroup"] else None
    stats = await LeaderboardService.get_user_score_and_rank(session, user_id=user_id, chat_id=chat_id)

    text = (
        f"🎖️ **Your Quiz Statistics** ({'Group' if chat_id else 'Global'})\n\n"
        f"🏆 **Rank:** #{stats['rank']}\n"
        f"⭐ **Total Score:** {stats['score']} points\n"
        f"✅ **Correct Answers:** {stats['correct']}\n"
        f"❌ **Wrong Answers:** {stats['wrong']}\n"
        f"⚡ **Fastest Answer Bonuses:** {stats['fastest']}\n"
        f"🎯 **Accuracy:** {stats['accuracy']}%\n"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("random"))
async def cmd_random(message: Message, session: AsyncSession, bot):
    chat = await get_or_create_chat(
        session=session,
        chat_id=message.chat.id,
        chat_title=message.chat.title,
        chat_type=message.chat.type
    )
    poll = await PollManager.send_quiz_poll(bot, session, chat)
    if not poll:
        await message.answer("⚠️ Could not generate quiz poll at this time.")
