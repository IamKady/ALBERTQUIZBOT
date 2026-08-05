import random
from typing import Optional
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.session import async_session
from bot.database.crud import get_active_chats, get_chat, get_expired_active_polls, mark_poll_closed
from bot.poll_manager.engine import PollManager
from bot.utils.logger import logger

class QuizScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

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
                    logger.warning(f"Poll send returned None for chat {chat_id}. Will retry in next cycle.")
        except Exception as e:
            logger.error(f"Error executing quiz trigger for chat {chat_id}: {e}")
        finally:
            if should_reschedule:
                logger.info(f"Next quiz for chat {chat_id} scheduled in {next_delay_secs} seconds ({next_delay_secs // 60} mins).")
                self.schedule_chat(chat_id, delay_seconds=next_delay_secs)

    async def cleanup_expired_polls(self):
        async with async_session() as session:
            expired_polls = await get_expired_active_polls(session)
            for poll in expired_polls:
                try:
                    # Stop poll on Telegram
                    await self.bot.stop_poll(chat_id=poll.chat_id, message_id=poll.message_id)
                except Exception as e:
                    logger.debug(f"Could not stop poll {poll.poll_id}: {e}")

                try:
                    # Automatically delete poll message after 10 minutes expiration as per requirement
                    await self.bot.delete_message(chat_id=poll.chat_id, message_id=poll.message_id)
                except Exception as e:
                    logger.debug(f"Could not delete message for poll {poll.poll_id}: {e}")

                await mark_poll_closed(session, poll.poll_id)
                logger.info(f"Cleaned up expired poll {poll.poll_id} in chat {poll.chat_id}.")
