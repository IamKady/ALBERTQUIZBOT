from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import UserScore, User

class LeaderboardService:
    @staticmethod
    async def get_top_users(
        session: AsyncSession,
        chat_id: Optional[int] = None,
        period: str = "all_time",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        
        stmt = select(
            User.user_id,
            User.username,
            User.first_name,
            func.sum(UserScore.score).label("total_score"),
            func.sum(UserScore.correct_count).label("total_correct"),
            func.sum(UserScore.wrong_count).label("total_wrong"),
            func.sum(UserScore.fastest_bonus_count).label("total_fastest")
        ).join(User, User.user_id == UserScore.user_id)

        if chat_id:
            stmt = stmt.where(UserScore.chat_id == chat_id)

        if period == "daily":
            start_date = now - timedelta(days=1)
            stmt = stmt.where(UserScore.updated_at >= start_date)
        elif period == "weekly":
            start_date = now - timedelta(weeks=1)
            stmt = stmt.where(UserScore.updated_at >= start_date)
        elif period == "monthly":
            start_date = now - timedelta(days=30)
            stmt = stmt.where(UserScore.updated_at >= start_date)

        stmt = stmt.group_by(User.user_id, User.username, User.first_name)\
                   .order_by(desc("total_score"))\
                   .limit(limit)

        res = await session.execute(stmt)
        rows = res.all()

        results = []
        for rank, row in enumerate(rows, 1):
            results.append({
                "rank": rank,
                "user_id": row.user_id,
                "username": row.username,
                "name": row.first_name or row.username or f"User_{row.user_id}",
                "score": int(row.total_score or 0),
                "correct": int(row.total_correct or 0),
                "wrong": int(row.total_wrong or 0),
                "fastest": int(row.total_fastest or 0)
            })
        return results

    @staticmethod
    async def get_user_score_and_rank(
        session: AsyncSession,
        user_id: int,
        chat_id: Optional[int] = None
    ) -> Dict[str, Any]:
        stmt = select(
            func.sum(UserScore.score).label("score"),
            func.sum(UserScore.correct_count).label("correct"),
            func.sum(UserScore.wrong_count).label("wrong"),
            func.sum(UserScore.fastest_bonus_count).label("fastest")
        ).where(UserScore.user_id == user_id)

        if chat_id:
            stmt = stmt.where(UserScore.chat_id == chat_id)

        res = await session.execute(stmt)
        row = res.first()
        score = int(row.score or 0) if row else 0
        correct = int(row.correct or 0) if row else 0
        wrong = int(row.wrong or 0) if row else 0
        fastest = int(row.fastest or 0) if row else 0

        # Calculate rank
        rank_stmt = select(func.count()).select_from(
            select(UserScore.user_id, func.sum(UserScore.score).label("s"))
            .group_by(UserScore.user_id)
            .having(func.sum(UserScore.score) > score)
            .subquery()
        )
        rank_res = await session.execute(rank_stmt)
        rank = (rank_res.scalar_one() or 0) + 1

        total_ans = correct + wrong
        accuracy = round((correct / total_ans * 100), 1) if total_ans > 0 else 0.0

        return {
            "score": score,
            "correct": correct,
            "wrong": wrong,
            "fastest": fastest,
            "accuracy": accuracy,
            "rank": rank
        }
