from types import TracebackType
from typing import Self

from tests.fakes.billing import (
    InMemoryStripeEventRepository,
    InMemorySubscriptionHistoryRepository,
    InMemorySubscriptionRepository,
)
from tests.fakes.checkins import InMemoryCheckinRepository, InMemoryObservationRepository
from tests.fakes.lesson_plans import InMemoryIfThenPlanRepository, InMemoryTaskRepository
from tests.fakes.lesson_progress import InMemoryLessonProgressRepository
from tests.fakes.lesson_schedule import InMemoryLessonScheduleRepository
from tests.fakes.plans import InMemoryConfidenceRepository, InMemoryPlanRepository
from tests.fakes.quiz import InMemoryQuizStateRepository
from tests.fakes.roleplay import InMemoryRoleplayRunRepository
from tests.fakes.saved_phrases import InMemorySavedPhraseRepository
from tests.fakes.scenario_answers import InMemoryScenarioAnswerRepository
from tests.fakes.sessions import InMemoryActiveDayRepository, InMemorySessionRepository


class FakeUnitOfWork:
    """In-memory UnitOfWork scaffold: records commit/rollback; rolls back on error."""

    def __init__(self) -> None:
        self.sessions = InMemorySessionRepository()
        self.active_days = InMemoryActiveDayRepository()
        self.quiz = InMemoryQuizStateRepository()
        self.lesson_schedule = InMemoryLessonScheduleRepository()
        self.lesson_progress = InMemoryLessonProgressRepository()
        self.scenario_answers = InMemoryScenarioAnswerRepository()
        self.plans = InMemoryPlanRepository()
        self.confidence = InMemoryConfidenceRepository()
        self.if_then_plans = InMemoryIfThenPlanRepository()
        self.tasks = InMemoryTaskRepository()
        self.subscriptions = InMemorySubscriptionRepository()
        self.subscription_history = InMemorySubscriptionHistoryRepository()
        self.stripe_events = InMemoryStripeEventRepository()
        self.roleplay_runs = InMemoryRoleplayRunRepository()
        self.saved_phrases = InMemorySavedPhraseRepository()
        self.checkins = InMemoryCheckinRepository()
        self.observations = InMemoryObservationRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
