"""Postgres repository for scenario picks (append-only)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.progress import ScenarioAnswer
from app.infrastructure.db.orm_models import ScenarioAnswerRow


class SqlScenarioAnswerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, answer: ScenarioAnswer) -> None:
        self._db.add(
            ScenarioAnswerRow(
                session_id=answer.session_id,
                lesson_id=answer.lesson_id,
                screen_id=answer.screen_id,
                answer_id=answer.answer_id,
                verdict=answer.verdict,
                answered_at=answer.answered_at,
            )
        )

    async def list_for_lesson(self, session_id: UUID, lesson_id: str) -> list[ScenarioAnswer]:
        result = await self._db.execute(
            select(ScenarioAnswerRow)
            .where(
                ScenarioAnswerRow.session_id == session_id,
                ScenarioAnswerRow.lesson_id == lesson_id,
            )
            .order_by(ScenarioAnswerRow.id)
        )
        return [
            ScenarioAnswer(
                row.session_id,
                row.lesson_id,
                row.screen_id,
                row.answer_id,
                row.verdict,
                row.answered_at,
            )
            for row in result.scalars()
        ]
