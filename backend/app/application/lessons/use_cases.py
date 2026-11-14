"""Lesson use cases."""

from app.application.lessons.access import LessonAccess, valid_variant
from app.application.lessons.dto import LessonView, ProgressView
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS, render_lesson
from app.domain.session.entities import Session


class GetLesson:
    """`GET /api/lessons/{id}`: the lesson rendered for the session, marked as started."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._content = content
        self._access = LessonAccess(uow, content, clock)

    async def execute(self, session: Session, lesson_id: str) -> LessonView:
        row = await self._access.open(session, lesson_id)
        progress = await self._access.get_or_start(session, lesson_id)
        variant = valid_variant(self._content, lesson_id, progress.variant)
        data = self._content.render_lesson(
            lesson_id,
            session.recipient_key or "",
            variant,
            runtime_values=dict.fromkeys(RUNTIME_PLACEHOLDERS, ""),
        )
        return LessonView(
            lesson=render_lesson(data, variant, is_first_lesson=row.seq == 0),
            unlock_on=row.unlock_on,
            progress=ProgressView(progress.step, progress.started_at, progress.done_at),
        )
