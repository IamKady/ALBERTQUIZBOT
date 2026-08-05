from datetime import datetime, timedelta, timezone
from typing import Optional
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Question, Chat, ActivePoll
from bot.poll_manager.question_selector import QuestionSelector
from bot.database.crud import create_active_poll, get_active_chat_polls, mark_poll_closed
from bot.utils.logger import logger

class PollManager:
    @staticmethod
    def sanitize_text(text: str, max_len: int) -> str:
        if not text:
            return ""
        return text[:max_len-3] + "..." if len(text) > max_len else text

    @classmethod
    async def send_quiz_poll(cls, bot: Bot, session: AsyncSession, chat: Chat) -> Optional[ActivePoll]:
        # Delete any previous active poll in this chat when a new one arrives
        try:
            previous_polls = await get_active_chat_polls(session, chat.chat_id)
            for prev_poll in previous_polls:
                try:
                    await bot.stop_poll(chat_id=prev_poll.chat_id, message_id=prev_poll.message_id)
                except Exception:
                    pass
                try:
                    await bot.delete_message(chat_id=prev_poll.chat_id, message_id=prev_poll.message_id)
                except Exception:
                    pass
                await mark_poll_closed(session, prev_poll.poll_id)
        except Exception as e:
            logger.debug(f"Previous poll cleanup warning for chat {chat.chat_id}: {e}")

        question: Optional[Question] = await QuestionSelector.get_next_question(session, chat)
        if not question:
            logger.warning(f"Could not fetch question for chat {chat.chat_id}")
            return None

        category_emojis = {
            "General Knowledge": "💡", "General Science": "🔬", "World History": "📜",
            "Geography": "🌍", "English": "✍️", "Mathematics": "📐", "Computer": "💻",
            "Technology": "🚀", "Sports": "🏆", "Current Affairs": "📰", "Funny Quiz": "🤪",
            "Logic": "🧠", "Mixed Category": "🔀"
        }
        emoji = category_emojis.get(question.category, "🎯")
        header = f"{emoji} {question.category} ({question.difficulty})"
        
        # Clean question text if it accidentally contains leading brackets
        raw_q = question.question_text
        if raw_q.startswith("["):
            raw_q = raw_q.split("]", 1)[-1].strip()

        question_text = cls.sanitize_text(f"{header}\n\n{raw_q}", 300)
        options = [
            cls.sanitize_text(question.option_a, 100),
            cls.sanitize_text(question.option_b, 100),
            cls.sanitize_text(question.option_c, 100),
            cls.sanitize_text(question.option_d, 100),
        ]
        explanation = cls.sanitize_text(question.explanation or "", 200)

        quiz_duration = chat.quiz_duration_mins or 10
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=quiz_duration)

        try:
            message = await bot.send_poll(
                chat_id=chat.chat_id,
                question=question_text,
                options=options,
                type="quiz",
                correct_option_id=question.correct_option,
                explanation=explanation if explanation else None,
                is_anonymous=False,  # Essential to track individual user poll answers!
                open_period=quiz_duration * 60  # Auto close poll on Telegram side
            )

            active_poll = await create_active_poll(
                session=session,
                poll_id=message.poll.id,
                chat_id=chat.chat_id,
                message_id=message.message_id,
                question_id=question.id,
                expires_at=expires_at
            )
            logger.info(f"Quiz poll sent to chat {chat.chat_id} (Poll ID: {message.poll.id})")
            return active_poll
        except Exception as e:
            logger.error(f"Failed to send quiz poll to chat {chat.chat_id}: {e}")
            return None
