import json
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Question
from bot.utils.logger import logger

async def export_questions_to_json(session: AsyncSession, filepath: str = "questions_export.json") -> int:
    stmt = select(Question)
    res = await session.execute(stmt)
    questions = res.scalars().all()

    data = [q.to_dict() for q in questions]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Exported {len(data)} questions to {filepath}")
    return len(data)
