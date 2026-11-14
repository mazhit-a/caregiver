"""`POST /api/lessons/{id}/complete`: mark the lesson done; return the wrap and what comes next."""

from app.application.lessons.access import LessonAccess, valid_variant
from app.application.lessons.dto import CompleteView, NextLessonView
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.lessons.screens import (
    RUNTIME_PLACEHOLDERS,
    SCREEN_RENDERERS,
    RenderContext,
    visible_screens,
)
from app.domain.plan.entities import StoredPlan
from app.domain.plan.errors import NoPlan
from app.domain.schedule.entities import ScheduledLesson
from app.domain.session.entities import Session

WRAP_TYPE = "wrap"


class CompleteLesson:
    """Same access checks as the lesson read (a locked lesson is 423). The first call sets
    `done_at`; later calls keep it. The next lesson is the following built lesson of the
    schedule, with the reason of its module and its unlock date."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._access = LessonAccess(uow, content, clock)

    async def execute(self, session: Session, lesson_id: str) -> CompleteView:
        row = await self._access.open(session, lesson_id)
        progress = await self._access.get_or_start(session, lesson_id)
        done_at = progress.done_at or session.app_now(self._clock.now())
        async with self._uow:
            if progress.done_at is None:
                progress.done_at = done_at
                await self._uow.lesson_progress.save(progress)
                await self._uow.commit()
            schedule = await self._uow.lesson_schedule.list_for_session(session.id)
            stored = await self._uow.plans.get(session.id)
        if stored is None:
            raise NoPlan()  # unreachable after `open`, kept for the type checker
        variant = valid_variant(self._content, lesson_id, progress.variant)
        data = self._content.render_lesson(
            lesson_id,
            session.recipient_key or "",
            variant,
            runtime_values=dict.fromkeys(RUNTIME_PLACEHOLDERS, ""),
            display_name=session.display_name,
        )
        wrap = next((s for s in visible_screens(data, variant) if s["type"] == WRAP_TYPE), None)
        ctx = RenderContext(variant, data["pattern"], row.seq == 0)
        following = next((s for s in schedule if s.seq == row.seq + 1), None)
        next_lesson = None if following is None else _next_lesson(stored, following)
        all_done = None if next_lesson or wrap is None else wrap.get("allDoneLine")
        return CompleteView(
            lesson_id,
            done_at,
            None if wrap is None else SCREEN_RENDERERS[WRAP_TYPE](wrap, ctx),
            next_lesson,
            all_done,
        )


def _next_lesson(stored: StoredPlan, following: ScheduledLesson) -> NextLessonView | None:
    for module in stored.plan.modules:
        for lesson in module.lessons:
            if lesson.id == following.lesson_id:
                return NextLessonView(
                    lesson.id, lesson.title, module.id, module.reason, following.unlock_on
                )
    return None
