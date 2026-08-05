from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, Boolean, Integer, Text, DateTime
from bot.models.base import Base

class Chat(Base):
    __tablename__ = "chats"

    chat_id = Column(BigInteger, primary_key=True, autoincrement=False)
    chat_title = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    min_interval_mins = Column(Integer, default=10)
    max_interval_mins = Column(Integer, default=10)
    quiz_duration_mins = Column(Integer, default=10)
    categories_enabled = Column(Text, default="")  # comma separated categories or empty for all
    mixed_mode = Column(Boolean, default=True)
    language = Column(String(10), default="en")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
