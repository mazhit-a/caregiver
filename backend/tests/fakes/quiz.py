from dataclasses import replace
from uuid import UUID

from app.domain.quiz.entities import QuizState


class InMemoryQuizStateRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, QuizState] = {}

    async def get(self, session_id: UUID) -> QuizState | None:
        stored = self.rows.get(session_id)
        return _copy(stored) if stored else None

    async def save(self, state: QuizState) -> None:
        self.rows[state.session_id] = _copy(state)


def _copy(state: QuizState) -> QuizState:
    return replace(state, answers=dict(state.answers), tags=list(state.tags))
