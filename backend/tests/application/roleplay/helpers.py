from dataclasses import dataclass, field, replace
from datetime import timedelta
from uuid import UUID

from app.application.ports import Coach
from app.application.roleplay.dto import StartView
from app.application.roleplay.finish import FinishRoleplay
from app.application.roleplay.limiter import LlmConcurrencyLimiter
from app.application.roleplay.start import StartRoleplay
from app.application.roleplay.turn import SubmitRoleplayTurn
from app.domain.lessons.progress import LessonProgress
from app.domain.roleplay.run import RunContext
from app.domain.roleplay.verdict import CoachVerdict, Goals
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.rate_limit import InMemoryRateLimiter
from tests.application.lessons.test_get_lesson import with_plan
from tests.fakes.clock import FixedClock
from tests.fakes.roleplay import PERFECT
from tests.fakes.sessions import FakeIdGenerator
from tests.fakes.unit_of_work import FakeUnitOfWork


@dataclass
class Rig:
    uow: FakeUnitOfWork
    clock: FixedClock
    content: JsonContentProvider
    session: Session
    llm_limiter: LlmConcurrencyLimiter
    ids: FakeIdGenerator = field(default_factory=FakeIdGenerator)

    def start_use_case(self) -> StartRoleplay:
        return StartRoleplay(self.uow, self.content, self.clock, self.ids)

    def finish_use_case(self) -> FinishRoleplay:
        return FinishRoleplay(self.uow, self.content, self.clock)

    def turn_use_case(
        self, coach: Coach, deadline: float = 5.0, per_hour: int = 40
    ) -> SubmitRoleplayTurn:
        return SubmitRoleplayTurn(
            self.uow,
            self.content,
            coach,
            self.clock,
            InMemoryRateLimiter(per_hour),
            self.llm_limiter,
            deadline,
        )

    async def start(
        self, context: RunContext = RunContext.LESSON, variant: str | None = "phone"
    ) -> StartView:
        if variant is not None:
            await self.uow.lesson_progress.save(
                LessonProgress(self.session.id, "m1_l1", self.clock.now(), variant=variant)
            )
        view = await self.start_use_case().execute(self.session, "m1_l1", context)
        return view


async def make_rig(uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider) -> Rig:
    session = await with_plan(uow, clock, content)
    session.clock_offset = timedelta(days=2)
    return Rig(uow, clock, content, session, LlmConcurrencyLimiter(4))


def verdict(notice: bool, reassure: bool, offer: bool, **changes: object) -> CoachVerdict:
    return replace(PERFECT, goals=Goals(notice, reassure, offer), **changes)  # type: ignore[arg-type]


def run_id(view: StartView) -> UUID:
    return view.run_id
