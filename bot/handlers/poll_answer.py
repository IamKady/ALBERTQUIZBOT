from aiogram import Router
from aiogram.types import PollAnswer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import (
    get_or_create_user,
    get_active_poll,
    mark_poll_fastest_claimed,
    record_user_answer
)
from bot.models import Question
from bot.utils.logger import logger

router = Router()

@router.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer, session: AsyncSession):
    user = poll_answer.user
    if not user:
        return

    # Ensure user exists in DB
    await get_or_create_user(
        session=session,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    poll_id = poll_answer.poll_id
    active_poll = await get_active_poll(session, poll_id)
    if not active_poll:
        logger.debug(f"Poll answer received for untracked poll ID {poll_id}")
        return

    # Fetch question to compare option
    q_stmt = select(Question).where(Question.id == active_poll.question_id)
    q_res = await session.execute(q_stmt)
    question = q_res.scalar_one_or_none()
    if not question:
        return

    selected_option = poll_answer.option_ids[0] if poll_answer.option_ids else -1
    is_correct = (selected_option == question.correct_option)

    is_fastest = False
    if is_correct:
        is_fastest = await mark_poll_fastest_claimed(session, poll_id)

    pts, score_obj = await record_user_answer(
        session=session,
        user_id=user.id,
        chat_id=active_poll.chat_id,
        is_correct=is_correct,
        is_fastest=is_fastest
    )

    fastest_msg = " ⚡ (Fastest Answer Bonus +2)" if is_fastest else ""
    logger.info(
        f"User {user.first_name} ({user.id}) answered poll {poll_id}: "
        f"Correct={is_correct}{fastest_msg}. Awarded {pts} points."
    )
