import random
from typing import Optional
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.session import async_session
from bot.database.crud import get_active_chats, get_chat, get_expired_active_polls, mark_poll_closed, get_active_chat_polls
from bot.poll_manager.engine import PollManager
from bot.utils.logger import logger

class QuizScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=timezone.utc)

    def start(self):
        if not self.scheduler.running:
            # Add cleanup job for expired polls running every 30 seconds
            self.scheduler.add_job(
                self.cleanup_expired_polls,
                trigger="interval",
                seconds=30,
                id="expired_polls_cleanup",
                replace_existing=True
            )
            # Add watchdog job to ensure all active chats stay scheduled every 2 minutes
            self.scheduler.add_job(
                self.watchdog_reschedule_active_chats,
                trigger="interval",
                minutes=2,
                id="active_chats_watchdog",
                replace_existing=True
            )
            self.scheduler.start()
            logger.info("Quiz Scheduler started with active watchdog.")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Quiz Scheduler stopped.")

    def schedule_chat(self, chat_id: int, delay_seconds: Optional[int] = None):
        job_id = f"quiz_job_{chat_id}"
        if delay_seconds is None:
            # Pick random delay between 5 seconds (initial boot) or random interval range
            delay_seconds = random.randint(5, 30)

        run_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        
        self.scheduler.add_job(
            self._trigger_chat_quiz,
            trigger=DateTrigger(run_date=run_time),
            args=[chat_id],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Scheduled next quiz for chat {chat_id} in {delay_seconds} seconds (at {run_time}).")

    def unschedule_chat(self, chat_id: int):
        job_id = f"quiz_job_{chat_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled quiz job for chat {chat_id}.")

    async def initialize_all_active_chats(self):
        async with async_session() as session:
            chats = await get_active_chats(session)
            logger.info(f"Found {len(chats)} active chats to schedule.")
            for chat in chats:
                self.schedule_chat(chat.chat_id, delay_seconds=random.randint(5, 30))

    async def watchdog_reschedule_active_chats(self):
        try:
            async with async_session() as session:
                chats = await get_active_chats(session)
                for chat in chats:
                    job_id = f"quiz_job_{chat.chat_id}"
                    if not self.scheduler.get_job(job_id):
                        logger.warning(f"Watchdog: Active chat {chat.chat_id} has no running quiz job. Scheduling now.")
                        self.schedule_chat(chat.chat_id, delay_seconds=random.randint(5, 20))
        except Exception as e:
            logger.error(f"Error in watchdog_reschedule_active_chats: {e}")

    async def _trigger_chat_quiz(self, chat_id: int):
        next_delay_secs = 600  # Default 10 minutes fallback
        should_reschedule = True
        try:
            async with async_session() as session:
                chat = await get_chat(session, chat_id)
                if not chat or not chat.is_active:
                    logger.info(f"Chat {chat_id} is inactive or not found. Skipping quiz trigger.")
                    should_reschedule = False
                    return

                # Calculate next interval for this chat
                min_m = chat.min_interval_mins or 10
                max_m = chat.max_interval_mins or 10
                if max_m < min_m:
                    max_m = min_m
                
                if min_m == max_m:
                    next_interval_mins = min_m
                else:
                    possible_intervals = [10, 15, 25, 40, 60, 120]
                    valid_intervals = [i for i in possible_intervals if min_m <= i <= max_m]
                    if valid_intervals:
                        next_interval_mins = random.choice(valid_intervals)
                    else:
                        next_interval_mins = random.randint(min_m, max_m)

                next_delay_secs = next_interval_mins * 60

                # Send quiz poll
                poll = await PollManager.send_quiz_poll(self.bot, session, chat)
                if poll:
                    logger.info(f"Quiz poll successfully sent to chat {chat_id}.")
                else:
                    next_delay_secs = 30  # Quick retry in 30 seconds if poll creation failed
                    logger.warning(f"Poll send returned None for chat {chat_id}. Will retry in {next_delay_secs} seconds.")
        except Exception as e:
            logger.error(f"Error executing quiz trigger for chat {chat_id}: {e}")
        finally:
            if should_reschedule:
                logger.info(f"Next quiz for chat {chat_id} scheduled in {next_delay_secs} seconds ({next_delay_secs // 60} mins).")
                self.schedule_chat(chat_id, delay_seconds=next_delay_secs)

    async def cleanup_expired_polls(self):
        await cleanup_expired_polls(self.bot)


async def cleanup_expired_polls(bot: Bot) -> int:
    """Closes and deletes all expired active polls."""
    cleaned = 0
    async with async_session() as session:
        expired_polls = await get_expired_active_polls(session)
        for poll in expired_polls:
            try:
                # Stop poll on Telegram
                await bot.stop_poll(chat_id=poll.chat_id, message_id=poll.message_id)
            except Exception as e:
                logger.debug(f"Could not stop poll {poll.poll_id}: {e}")

            try:
                # Automatically delete poll message after expiration
                await bot.delete_message(chat_id=poll.chat_id, message_id=poll.message_id)
            except Exception as e:
                logger.debug(f"Could not delete message for poll {poll.poll_id}: {e}")

            try:
                await mark_poll_closed(session, poll.poll_id)
                cleaned += 1
                logger.info(f"Cleaned up expired poll {poll.poll_id} in chat {poll.chat_id}.")
            except Exception as e:
                await session.rollback()
                logger.error(f"Could not mark poll closed {poll.poll_id}: {e}")
    return cleaned


async def run_cron_cycle(bot: Bot) -> dict:
    """
    Executes a serverless cron maintenance cycle:
    1. Cleans up expired active polls across all chats.
    2. Dispatches scheduled quiz polls to active chats that are due.
    """
    logger.info("Executing serverless cron maintenance cycle...")
    cleaned_count = await cleanup_expired_polls(bot)
    sent_count = 0
    chat_details = []

    from sqlalchemy import select, func
    from bot.models import ActivePoll

    async with async_session() as session:
        chats = await get_active_chats(session)
        chat_ids = [c.chat_id for c in chats]
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for chat_id in chat_ids:
            chat_info = {
                "chat_id": chat_id,
                "title": str(chat_id),
                "min_interval_mins": 10,
                "is_due": False,
                "action": "skipped"
            }

            try:
                chat = await get_chat(session, chat_id)
                if not chat or not chat.is_active:
                    chat_info["action"] = "inactive_or_not_found"
                    chat_details.append(chat_info)
                    continue

                chat_title = chat.chat_title or str(chat_id)
                min_interval = chat.min_interval_mins or 10
                chat_info["title"] = chat_title
                chat_info["min_interval_mins"] = min_interval

                # If chat has any active (unexpired) poll right now, skip sending another
                open_polls = await get_active_chat_polls(session, chat_id)
                active_open_polls = [
                    p for p in open_polls
                    if (p.expires_at.replace(tzinfo=None) if p.expires_at.tzinfo else p.expires_at) > now
                ]
                if active_open_polls:
                    chat_info["action"] = "skipped_active_poll_in_progress"
                    chat_info["active_poll_id"] = active_open_polls[0].poll_id
                    chat_details.append(chat_info)
                    continue

                # Check when the last poll was sent
                stmt = select(func.max(ActivePoll.created_at)).where(ActivePoll.chat_id == chat_id)
                res = await session.execute(stmt)
                last_poll_time = res.scalar_one_or_none()

                is_due = False
                if last_poll_time is None:
                    is_due = True
                    chat_info["last_poll_time"] = None
                    chat_info["elapsed_seconds"] = None
                else:
                    if last_poll_time.tzinfo is not None:
                        last_poll_time = last_poll_time.astimezone(timezone.utc).replace(tzinfo=None)
                    elapsed = (now - last_poll_time).total_seconds()
                    chat_info["last_poll_time"] = last_poll_time.isoformat()
                    chat_info["elapsed_seconds"] = int(elapsed)
                    # 45 seconds tolerance for cron jitter (e.g. cron triggers at 9m50s)
                    if elapsed >= ((min_interval * 60) - 45):
                        is_due = True

                chat_info["is_due"] = is_due

                if is_due:
                    poll = await PollManager.send_quiz_poll(bot, session, chat)
                    if poll:
                        sent_count += 1
                        chat_info["action"] = "quiz_dispatched"
                        chat_info["poll_id"] = poll.poll_id
                        logger.info(f"Cron cycle dispatched quiz to chat {chat_id}")
                    else:
                        chat_info["action"] = "poll_generation_failed"
                        logger.warning(f"Poll generation returned None for chat {chat_id}")
                else:
                    chat_info["action"] = "not_due_yet"

            except Exception as e:
                await session.rollback()
                chat_info["action"] = f"error: {str(e)}"
                logger.error(f"Error checking/sending quiz for chat {chat_id} in cron cycle: {e}")

            chat_details.append(chat_info)

    result = {
        "status": "success",
        "cleaned_polls": cleaned_count,
        "quizzes_sent": sent_count,
        "total_active_chats": len(chats),
        "chat_details": chat_details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    logger.info(f"Cron cycle completed: {result}")
    return result

