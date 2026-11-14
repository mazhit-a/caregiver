from uuid import UUID

from app.domain.schedule.entities import ScheduledLesson


class InMemoryLessonScheduleRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, dict[str, ScheduledLesson]] = {}

    async def list_for_session(self, session_id: UUID) -> list[ScheduledLesson]:
        return sorted(self.rows.get(session_id, {}).values(), key=lambda s: s.seq)

    async def add_many(self, session_id: UUID, lessons: list[ScheduledLesson]) -> None:
        rows = self.rows.setdefault(session_id, {})
        for lesson in lessons:
            if lesson.lesson_id in rows:
                raise ValueError("duplicate lesson_id for session")
            rows[lesson.lesson_id] = lesson
