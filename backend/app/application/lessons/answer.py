"""`POST /api/lessons/{id}/answers`: dispatch an answer to the handler of the screen's type."""

from collections.abc import Mapping

from app.application.lessons.access import LessonAccess, valid_variant
from app.application.lessons.dto import AnswerView
from app.application.lessons.handlers import SCREEN_HANDLERS, AnswerContext, ScreenHandler
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.lessons.errors import InvalidScreenAnswer, UnknownScreen
from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS, visible_screens
from app.domain.session.entities import Session


class AnswerLesson:
    """Same access checks as the lesson read, then: screen must be visible (else 422
    `unknown_screen`), its type must have a handler and accept the value (else 422
    `invalid_screen_answer`). Server-only fields are looked up from the content file here.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        content: ContentProvider,
        clock: Clock,
        handlers: Mapping[str, ScreenHandler] | None = None,
    ) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._access = LessonAccess(uow, content, clock)
        self._handlers = SCREEN_HANDLERS if handlers is None else handlers

    async def execute(
        self, session: Session, lesson_id: str, screen_id: str, value: object
    ) -> AnswerView:
        await self._access.open(session, lesson_id)
        progress = await self._access.get_or_start(session, lesson_id)
        variant = valid_variant(self._content, lesson_id, progress.variant)
        data = self._content.render_lesson(
            lesson_id,
            session.recipient_key or "",
            variant,
            runtime_values=dict.fromkeys(RUNTIME_PLACEHOLDERS, ""),
        )
        screen = next((s for s in visible_screens(data, variant) if s["id"] == screen_id), None)
        if screen is None:
            raise UnknownScreen(lesson_id, screen_id)
        handler = self._handlers.get(screen["type"])
        if handler is None:
            raise InvalidScreenAnswer(screen_id, "screen_takes_no_answer")
        answered_at = session.app_now(self._clock.now())
        outcome = handler(AnswerContext(session.id, lesson_id, screen, variant, answered_at), value)
        progress.screen_answers.update(outcome.stored)
        if outcome.variant is not None:
            progress.variant = outcome.variant
        async with self._uow:
            await self._uow.lesson_progress.save(progress)
            if outcome.scenario_answer is not None:
                await self._uow.scenario_answers.add(outcome.scenario_answer)
            await self._uow.commit()
        return AnswerView(screen_id, screen["type"], outcome.result)
