from datetime import datetime, timezone
from sqlalchemy import Column, String, BigInteger, Integer, DateTime, Boolean
from bot.models.base import Base

class ActivePoll(Base):
    __tablename__ = "active_polls"

    poll_id = Column(String(255), primary_key=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    message_id = Column(Integer, nullable=False)
    question_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    closed = Column(Boolean, default=False)
    fastest_answered = Column(Boolean, default=False)
