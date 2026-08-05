import random
from typing import Optional, List
from sqlalchemy import select, func, delete, not_
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Question, UsedQuestion, Chat
from bot.utils.logger import logger

class QuestionSelector:
    @staticmethod
    async def get_next_question(session: AsyncSession, chat: Chat) -> Optional[Question]:
        # Parse enabled categories
        enabled_cats = []
        if chat.categories_enabled and chat.categories_enabled.strip():
            enabled_cats = [c.strip() for c in chat.categories_enabled.split(",") if c.strip()]

        # Query base for questions
        base_query = select(Question.id)
        if enabled_cats and not chat.mixed_mode:
            base_query = base_query.where(Question.category.in_(enabled_cats))

        # Get list of used question ids for this chat
        used_stmt = select(UsedQuestion.question_id).where(UsedQuestion.chat_id == chat.chat_id)
        used_res = await session.execute(used_stmt)
        used_ids = set(used_res.scalars().all())

        # Select unused questions
        unused_query = base_query.where(not_(Question.id.in_(used_ids))) if used_ids else base_query
        res = await session.execute(unused_query)
        unused_ids = list(res.scalars().all())

        if not unused_ids:
            logger.info(f"Chat {chat.chat_id} exhausted all questions in cycle. Resetting used questions history...")
            # Clear used questions history for this chat to start a new cycle!
            await session.execute(
                delete(UsedQuestion).where(UsedQuestion.chat_id == chat.chat_id)
            )
            await session.commit()

            # Re-fetch all ids
            res = await session.execute(base_query)
            unused_ids = list(res.scalars().all())

        if not unused_ids:
            logger.warning("No questions found in database!")
            return None

        # Pick random question ID
        selected_id = random.choice(unused_ids)

        # Record question as used for this chat
        used_q = UsedQuestion(chat_id=chat.chat_id, question_id=selected_id)
        session.add(used_q)
        await session.commit()

        # Retrieve full question object
        q_res = await session.execute(select(Question).where(Question.id == selected_id))
        return q_res.scalar_one_or_none()
