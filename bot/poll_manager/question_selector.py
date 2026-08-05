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

        # Subquery for used questions in this chat
        used_subquery = select(UsedQuestion.question_id).where(UsedQuestion.chat_id == chat.chat_id)

        # Select unused questions using SQL subquery
        unused_query = base_query.where(Question.id.not_in(used_subquery))
        res = await session.execute(unused_query)
        unused_ids = list(res.scalars().all())

        if not unused_ids:
            # Check if base query has any questions at all (e.g. if category filter matched nothing)
            base_res = await session.execute(base_query)
            all_ids = list(base_res.scalars().all())

            if all_ids:
                logger.info(f"Chat {chat.chat_id} exhausted all questions in current cycle. Resetting used questions history...")
                await session.execute(
                    delete(UsedQuestion).where(UsedQuestion.chat_id == chat.chat_id)
                )
                await session.commit()
                unused_ids = all_ids
            else:
                # Fallback to all questions across all categories if specific category filter yielded 0 questions
                logger.warning(f"No questions matched category filter for chat {chat.chat_id}. Falling back to all questions.")
                all_res = await session.execute(select(Question.id))
                unused_ids = list(all_res.scalars().all())

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
