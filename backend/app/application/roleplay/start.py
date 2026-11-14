"""`StartRoleplay`: open a run and serve its rounds."""

from app.application.lessons.access import LessonAccess, valid_variant
from app.application.ports import Clock, ContentProvider, IdGenerator, UnitOfWork
from app.application.roleplay.dto import StartView
from app.application.roleplay.lesson_source import render, roleplay_screen, rounds_for
from app.application.roleplay.runs import save_run
from app.domain.roleplay.run import RoleplayRun, RunContext, RunRecord
from app.domain.session.entities import Session


class StartRoleplay:
    """Same access checks as the lesson read. The variant is the one stored in lesson progress;
    `lesson` serves the role-play screen's rounds, `practice_round` serves day 2's."""

    def __init__(
        self, uow: UnitOfWork, content: ContentProvider, clock: Clock, ids: IdGenerator
    ) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._ids = ids
        self._access = LessonAccess(uow, content, clock)

    async def execute(self, session: Session, lesson_id: str, context: RunContext) -> StartView:
        await self._access.open(session, lesson_id)
        progress = await self._access.get_or_start(session, lesson_id)
        variant = valid_variant(self._content, lesson_id, progress.variant)
        lesson = render(self._content, session, lesson_id, variant)
        rounds = rounds_for(lesson, context, variant)
        screen = roleplay_screen(lesson)
        record = RunRecord(
            id=self._ids.new_id(),
            session_id=session.id,
            lesson_id=lesson_id,
            context=context,
            variant=variant,
            started_at=session.app_now(self._clock.now()),
            run=RoleplayRun(rounds_total=len(rounds)),
        )
        await save_run(self._uow, record)
        in_lesson = context is RunContext.LESSON
        title = screen["title"] if in_lesson else lesson["day2"]["practiceRound"]["title"]
        goals = screen["goals"] if in_lesson else lesson["day2"]["practiceRound"]["goals"]
        return StartView(
            run_id=record.id,
            lesson_id=lesson_id,
            context=context,
            variant=variant,
            rounds=rounds,
            title=title,
            goals=tuple(goals),
            intro=screen["intro"] if in_lesson else None,
            labels=dict(screen["labels"]),
        )
