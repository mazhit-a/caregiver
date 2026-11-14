"""Lesson use cases."""

from app.application.lessons.access import LessonAccess, valid_variant
from app.application.lessons.dto import LessonView, ProgressView, RecapView
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS, render_lesson
from app.domain.phrases.entities import RECAP_PHRASE_MARKER, fill_recap
from app.domain.session.entities import Session


class GetLesson:
    """`GET /api/lessons/{id}`: the lesson rendered for the session, marked as started."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
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
            recap=await self._recap(session, row.seq),
        )

    async def _recap(self, session: Session, seq: int) -> RecapView | None:
        """The previous lesson's `recapForNextLesson` with the phrase saved for it; lesson 1
        has none. `{savedPhrase}` is filled here, at the point of use."""
        if seq == 0:
            return None
        async with self._uow:
            schedule = await self._uow.lesson_schedule.list_for_session(session.id)
            phrases = await self._uow.saved_phrases.list_for_session(session.id)
        previous = next((s for s in schedule if s.seq == seq - 1), None)
        if previous is None:
            return None
        saved = [p.text for p in phrases if p.lesson_id == previous.lesson_id]
        data = self._content.render_lesson(
            previous.lesson_id,
            session.recipient_key or "",
            None,
            runtime_values={
                **dict.fromkeys(RUNTIME_PLACEHOLDERS, ""),
                "savedPhrase": RECAP_PHRASE_MARKER,
            },
        )
        text = fill_recap(data["recapForNextLesson"]["text"], saved[-1] if saved else None)
        return RecapView(previous.lesson_id, text)
