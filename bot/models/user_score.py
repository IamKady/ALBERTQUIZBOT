from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, DateTime, Index
from bot.models.base import Base

class UserScore(Base):
    __tablename__ = "user_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    score = Column(Integer, default=0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    wrong_count = Column(Integer, default=0, nullable=False)
    fastest_bonus_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        kwargs.setdefault("score", 0)
        kwargs.setdefault("correct_count", 0)
        kwargs.setdefault("wrong_count", 0)
        kwargs.setdefault("fastest_bonus_count", 0)
        super().__init__(**kwargs)

    __table_args__ = (
        Index("ix_user_chat_score", "user_id", "chat_id", unique=True),
    )
