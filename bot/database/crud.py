from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, update, func, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config.settings import settings
from bot.models import Chat, Question, User, UserScore, ActivePoll, UsedQuestion
from bot.utils.logger import logger

def utc_now() -> datetime:
    """Returns naive UTC datetime matching SQLAlchemy DateTime (without timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

async def get_or_create_chat(
    session: AsyncSession,
    chat_id: int,
    chat_title: Optional[str] = None,
    chat_type: str = "group"
) -> Chat:
    stmt = select(Chat).where(Chat.chat_id == chat_id)
    res = await session.execute(stmt)
    chat = res.scalar_one_or_none()
    if not chat:
        chat = Chat(
            chat_id=chat_id,
            chat_title=chat_title,
            chat_type=chat_type,
            is_active=True,
            min_interval_mins=settings.DEFAULT_MIN_INTERVAL,
            max_interval_mins=settings.DEFAULT_MAX_INTERVAL,
            quiz_duration_mins=settings.DEFAULT_QUIZ_DURATION
        )
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
    else:
        updated = False
        if chat_title and chat.chat_title != chat_title:
            chat.chat_title = chat_title
            updated = True
        if chat.min_interval_mins is None:
            chat.min_interval_mins = settings.DEFAULT_MIN_INTERVAL
            updated = True
        if chat.max_interval_mins is None:
            chat.max_interval_mins = settings.DEFAULT_MAX_INTERVAL
            updated = True
        if updated:
            await session.commit()
    return chat

async def get_chat(session: AsyncSession, chat_id: int) -> Optional[Chat]:
    stmt = select(Chat).where(Chat.chat_id == chat_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()

async def get_active_chats(session: AsyncSession) -> List[Chat]:
    stmt = select(Chat).where(Chat.is_active == True)
    res = await session.execute(stmt)
    return list(res.scalars().all())

async def update_chat(session: AsyncSession, chat_id: int, **kwargs) -> Optional[Chat]:
    stmt = select(Chat).where(Chat.chat_id == chat_id)
    res = await session.execute(stmt)
    chat = res.scalar_one_or_none()
    if chat:
        for k, v in kwargs.items():
            if hasattr(chat, k):
                setattr(chat, k, v)
        await session.commit()
        await session.refresh(chat)
    return chat

async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None
) -> User:
    stmt = select(User).where(User.user_id == user_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        user = User(user_id=user_id, username=username, first_name=first_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        if username and user.username != username or first_name and user.first_name != first_name:
            user.username = username
            user.first_name = first_name
            await session.commit()
    return user

async def record_user_answer(
    session: AsyncSession,
    user_id: int,
    chat_id: int,
    is_correct: bool,
    is_fastest: bool = False
) -> Tuple[int, UserScore]:
    stmt = select(UserScore).where(UserScore.user_id == user_id, UserScore.chat_id == chat_id)
    res = await session.execute(stmt)
    user_score = res.scalar_one_or_none()

    points_awarded = 0
    if not user_score:
        user_score = UserScore(user_id=user_id, chat_id=chat_id)
        session.add(user_score)

    if is_correct:
        points_awarded += 5
        user_score.correct_count = (user_score.correct_count or 0) + 1
        if is_fastest:
            points_awarded += 2
            user_score.fastest_bonus_count = (user_score.fastest_bonus_count or 0) + 1
    else:
        user_score.wrong_count = (user_score.wrong_count or 0) + 1

    user_score.score = (user_score.score or 0) + points_awarded
    user_score.updated_at = utc_now()
    await session.commit()
    await session.refresh(user_score)
    return points_awarded, user_score

async def create_active_poll(
    session: AsyncSession,
    poll_id: str,
    chat_id: int,
    message_id: int,
    question_id: int,
    expires_at: datetime
) -> ActivePoll:
    if expires_at.tzinfo is not None:
        expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
    active_poll = ActivePoll(
        poll_id=poll_id,
        chat_id=chat_id,
        message_id=message_id,
        question_id=question_id,
        expires_at=expires_at
    )
    session.add(active_poll)
    await session.commit()
    return active_poll

async def get_active_poll(session: AsyncSession, poll_id: str) -> Optional[ActivePoll]:
    stmt = select(ActivePoll).where(ActivePoll.poll_id == poll_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()

async def get_expired_active_polls(session: AsyncSession) -> List[ActivePoll]:
    now = utc_now()
    stmt = select(ActivePoll).where(ActivePoll.closed == False, ActivePoll.expires_at <= now)
    res = await session.execute(stmt)
    return list(res.scalars().all())

async def get_active_chat_polls(session: AsyncSession, chat_id: int) -> List[ActivePoll]:
    stmt = select(ActivePoll).where(ActivePoll.closed == False, ActivePoll.chat_id == chat_id)
    res = await session.execute(stmt)
    return list(res.scalars().all())

async def mark_poll_closed(session: AsyncSession, poll_id: str):
    stmt = update(ActivePoll).where(ActivePoll.poll_id == poll_id).values(closed=True)
    await session.execute(stmt)
    await session.commit()

async def mark_poll_fastest_claimed(session: AsyncSession, poll_id: str) -> bool:
    stmt = select(ActivePoll).where(ActivePoll.poll_id == poll_id)
    res = await session.execute(stmt)
    poll = res.scalar_one_or_none()
    if poll and not poll.fastest_answered:
        poll.fastest_answered = True
        await session.commit()
        return True
    return False

async def get_global_stats(session: AsyncSession) -> Dict[str, Any]:
    q_count = (await session.execute(select(func.count(Question.id)))).scalar_one()
    c_count = (await session.execute(select(func.count(Chat.chat_id)))).scalar_one()
    u_count = (await session.execute(select(func.count(User.user_id)))).scalar_one()
    p_count = (await session.execute(select(func.count(ActivePoll.poll_id)))).scalar_one()
    scores_res = await session.execute(
        select(
            func.sum(UserScore.correct_count),
            func.sum(UserScore.wrong_count)
        )
    )
    correct, wrong = scores_res.first()
    correct = correct or 0
    wrong = wrong or 0
    total_answers = correct + wrong
    participation_pct = round((correct / total_answers * 100), 2) if total_answers > 0 else 0.0

    return {
        "total_questions": q_count,
        "total_chats": c_count,
        "total_users": u_count,
        "total_polls_sent": p_count,
        "correct_answers": correct,
        "wrong_answers": wrong,
        "participation_pct": participation_pct
    }
