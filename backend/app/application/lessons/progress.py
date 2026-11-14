"""`PUT /api/lessons/{id}/progress`: remember the screen the learner is on."""

from app.application.lessons.access import LessonAccess, valid_variant
from app.application.lessons.dto import ProgressView
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS, visible_screens
from app.domain.session.entities import Session


class SaveLessonStep:
    """Same access checks as the lesson read (a locked lesson is 423). The step must be a screen
    the learner can currently see (422 `invalid_lesson_step`); a done lesson keeps its step."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._access = LessonAccess(uow, content, clock)

    async def execute(self, session: Session, lesson_id: str, step: int) -> ProgressView:
        await self._access.open(session, lesson_id)
        progress = await self._access.get_or_start(session, lesson_id)
        variant = valid_variant(self._content, lesson_id, progress.variant)
        data = self._content.render_lesson(
            lesson_id,
            session.recipient_key or "",
            variant,
            runtime_values=dict.fromkeys(RUNTIME_PLACEHOLDERS, ""),
            display_name=session.display_name,
        )
        progress.move_to(step, len(visible_screens(data, variant)))
        async with self._uow:
            await self._uow.lesson_progress.save(progress)
            await self._uow.commit()
        return ProgressView(progress.step, progress.started_at, progress.done_at)
