from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, DateTime, Index
from bot.models.base import Base

class UsedQuestion(Base):
    __tablename__ = "used_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    used_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_chat_question", "chat_id", "question_id", unique=True),
    )
