import json
import csv
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Question
from bot.utils.logger import logger

async def import_questions_from_json(session: AsyncSession, filepath: str) -> int:
    with open(filepath, "r", encoding="utf-8") as f:
        items = json.load(f)

    imported_count = 0
    for item in items:
        # Check duplicate
        text = item.get("question_text")
        if not text:
            continue

        stmt = select(Question).where(Question.question_text == text)
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            continue

        options = item.get("options", [])
        q = Question(
            question_text=text,
            option_a=options[0] if len(options) > 0 else item.get("option_a", ""),
            option_b=options[1] if len(options) > 1 else item.get("option_b", ""),
            option_c=options[2] if len(options) > 2 else item.get("option_c", ""),
            option_d=options[3] if len(options) > 3 else item.get("option_d", ""),
            correct_option=item.get("correct_option", 0),
            category=item.get("category", "General Knowledge"),
            difficulty=item.get("difficulty", "Medium"),
            explanation=item.get("explanation", ""),
            source=item.get("source", "Import"),
            tags=item.get("tags", ""),
            language=item.get("language", "en")
        )
        session.add(q)
        imported_count += 1

    await session.commit()
    logger.info(f"Successfully imported {imported_count} new questions from {filepath}")
    return imported_count
