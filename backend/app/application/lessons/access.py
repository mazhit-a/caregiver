"""The checks every lesson route shares: plan, known id, built, unlocked; progress started."""

from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.application.schedule.use_cases import EnsureSchedule
from app.domain.lessons.errors import LessonLocked, LessonNotAvailable, UnknownLesson
from app.domain.lessons.progress import LessonProgress
from app.domain.plan.entities import StoredPlan
from app.domain.plan.errors import NoPlan
from app.domain.schedule.entities import PlanLessonRef, ScheduledLesson, UnlockRule
from app.domain.session.entities import Session


class LessonAccess:
    """Order of checks: no plan, unknown id (404 `unknown_lesson`), planned but unbuilt (404
    `lesson_not_available`), not unlocked yet (423 `lesson_locked`, `details.unlockOn`).
    The schedule is extended first, so a lesson built after the subscription started is found.
    """

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._ensure_schedule = EnsureSchedule(uow)

    async def open(self, session: Session, lesson_id: str) -> ScheduledLesson:
        if session.recipient_key is None:
            raise NoPlan()
        async with self._uow:
            stored = await self._uow.plans.get(session.id)
        if stored is None:
            raise NoPlan()
        refs = self._plan_lessons(stored)
        self._check_available(lesson_id, refs)
        today = session.app_today(self._clock.now())
        schedule = await self._ensure_schedule.execute(
            session.id,
            today,
            stored.lessons_per_week,
            refs,
            UnlockRule.from_pace(self._content.plan_rules().pace),
        )
        row = next((s for s in schedule if s.lesson_id == lesson_id), None)
        if row is None:
            raise LessonNotAvailable(lesson_id)
        if row.unlock_on > today:
            raise LessonLocked(lesson_id, row.unlock_on)
        return row

    async def get_or_start(self, session: Session, lesson_id: str) -> LessonProgress:
        async with self._uow:
            progress = await self._uow.lesson_progress.get(session.id, lesson_id)
            if progress is None:
                progress = LessonProgress(
                    session.id, lesson_id, started_at=session.app_now(self._clock.now())
                )
                await self._uow.lesson_progress.save(progress)
                await self._uow.commit()
        return progress

    def _plan_lessons(self, stored: StoredPlan) -> list[PlanLessonRef]:
        return plan_lesson_refs(self._content, stored)

    def _check_available(self, lesson_id: str, refs: list[PlanLessonRef]) -> None:
        by_id = {ref.lesson_id: ref for ref in refs}
        if lesson_id not in by_id and lesson_id not in self._content.lesson_ids():
            raise UnknownLesson(lesson_id)
        ref = by_id.get(lesson_id)
        if ref is None or not ref.built:
            raise LessonNotAvailable(lesson_id)


def plan_lesson_refs(content: ContentProvider, stored: StoredPlan) -> list[PlanLessonRef]:
    """The plan's lessons; built means flagged built in the current rules and a file exists."""
    files = set(content.lesson_ids())
    flags = {
        lesson.id: lesson.built
        for module in content.plan_rules().modules
        for lesson in module.lessons
    }
    return [
        PlanLessonRef(lesson.id, flags.get(lesson.id, lesson.built) is True and lesson.id in files)
        for module in stored.plan.modules
        for lesson in module.lessons
    ]


def valid_variant(content: ContentProvider, lesson_id: str, variant: str | None) -> str | None:
    """A stored variant the lesson no longer offers (content edit) is treated as unset."""
    if variant is not None and variant in content.lesson_variants(lesson_id):
        return variant
    return None
