from dataclasses import replace
from uuid import UUID

from app.domain.lessons.progress import LessonProgress


class InMemoryLessonProgressRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, str], LessonProgress] = {}

    async def get(self, session_id: UUID, lesson_id: str) -> LessonProgress | None:
        row = self.rows.get((session_id, lesson_id))
        return None if row is None else replace(row, screen_answers=dict(row.screen_answers))

    async def save(self, progress: LessonProgress) -> None:
        self.rows[(progress.session_id, progress.lesson_id)] = replace(
            progress, screen_answers=dict(progress.screen_answers)
        )
