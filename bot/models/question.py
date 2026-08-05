import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from bot.models.base import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    question_text = Column(Text, nullable=False)
    option_a = Column(String(255), nullable=False)
    option_b = Column(String(255), nullable=False)
    option_c = Column(String(255), nullable=False)
    option_d = Column(String(255), nullable=False)
    correct_option = Column(Integer, nullable=False)  # 0, 1, 2, or 3
    category = Column(String(100), nullable=False, index=True)
    difficulty = Column(String(20), nullable=False, default="Medium", index=True)
    explanation = Column(Text, nullable=True)
    source = Column(String(255), default="System")
    tags = Column(String(255), default="")
    language = Column(String(10), default="en", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_question_cat_diff", "category", "difficulty"),
        Index("ix_question_text_hash", "question_text"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "question_text": self.question_text,
            "options": [self.option_a, self.option_b, self.option_c, self.option_d],
            "correct_option": self.correct_option,
            "category": self.category,
            "difficulty": self.difficulty,
            "explanation": self.explanation,
            "source": self.source,
            "tags": self.tags,
            "language": self.language
        }
