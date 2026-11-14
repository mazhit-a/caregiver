"""Postgres repository for the saved quiz of a session."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.quiz.entities import QuizState
from app.infrastructure.db.mappers import quiz_state_to_domain
from app.infrastructure.db.orm_models import QuizStateRow


class SqlQuizStateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID) -> QuizState | None:
        result = await self._db.execute(
            select(QuizStateRow).where(QuizStateRow.session_id == session_id)
        )
        row = result.scalar_one_or_none()
        return quiz_state_to_domain(row) if row else None

    async def save(self, state: QuizState) -> None:
        values = {
            "answers": state.answers,
            "tags": state.tags,
            "branch": state.branch,
            "last_question_id": state.last_question_id,
            "completed_at": state.completed_at,
            "locked": state.locked,
            "health_answers_purged_at": state.health_answers_purged_at,
        }
        stmt = insert(QuizStateRow).values(session_id=state.session_id, **values)
        await self._db.execute(
            stmt.on_conflict_do_update(index_elements=[QuizStateRow.session_id], set_=values)
        )
