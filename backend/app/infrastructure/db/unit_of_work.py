"""SQLAlchemy unit of work: one AsyncSession per `async with`, repositories as attributes."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositories.checkins import (
    SqlCheckinRepository,
    SqlObservationRepository,
)
from app.infrastructure.db.repositories.confidence import SqlConfidenceRepository
from app.infrastructure.db.repositories.lesson_plans import (
    SqlIfThenPlanRepository,
    SqlTaskRepository,
)
from app.infrastructure.db.repositories.lesson_progress import SqlLessonProgressRepository
from app.infrastructure.db.repositories.lesson_schedule import SqlLessonScheduleRepository
from app.infrastructure.db.repositories.plans import SqlPlanRepository
from app.infrastructure.db.repositories.profiles import SqlProfileRepository
from app.infrastructure.db.repositories.quiz_states import SqlQuizStateRepository
from app.infrastructure.db.repositories.roleplay_runs import SqlRoleplayRunRepository
from app.infrastructure.db.repositories.saved_phrases import SqlSavedPhraseRepository
from app.infrastructure.db.repositories.scenario_answers import SqlScenarioAnswerRepository
from app.infrastructure.db.repositories.sessions import SqlActiveDayRepository, SqlSessionRepository
from app.infrastructure.db.repositories.stripe_events import SqlStripeEventRepository
from app.infrastructure.db.repositories.subscriptions import (
    SqlSubscriptionHistoryRepository,
    SqlSubscriptionRepository,
)
from app.infrastructure.db.repositories.visit_sheets import SqlVisitSheetRepository


class SqlAlchemyUnitOfWork:
    sessions: SqlSessionRepository
    active_days: SqlActiveDayRepository
    quiz: SqlQuizStateRepository
    lesson_schedule: SqlLessonScheduleRepository
    lesson_progress: SqlLessonProgressRepository
    scenario_answers: SqlScenarioAnswerRepository
    plans: SqlPlanRepository
    confidence: SqlConfidenceRepository
    if_then_plans: SqlIfThenPlanRepository
    tasks: SqlTaskRepository
    subscriptions: SqlSubscriptionRepository
    subscription_history: SqlSubscriptionHistoryRepository
    stripe_events: SqlStripeEventRepository
    roleplay_runs: SqlRoleplayRunRepository
    saved_phrases: SqlSavedPhraseRepository
    checkins: SqlCheckinRepository
    observations: SqlObservationRepository
    profiles: SqlProfileRepository
    visit_sheets: SqlVisitSheetRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory
        self._db: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._db = self._factory()
        self.sessions = SqlSessionRepository(self._db)
        self.active_days = SqlActiveDayRepository(self._db)
        self.quiz = SqlQuizStateRepository(self._db)
        self.lesson_schedule = SqlLessonScheduleRepository(self._db)
        self.lesson_progress = SqlLessonProgressRepository(self._db)
        self.scenario_answers = SqlScenarioAnswerRepository(self._db)
        self.plans = SqlPlanRepository(self._db)
        self.confidence = SqlConfidenceRepository(self._db)
        self.if_then_plans = SqlIfThenPlanRepository(self._db)
        self.tasks = SqlTaskRepository(self._db)
        self.subscriptions = SqlSubscriptionRepository(self._db)
        self.subscription_history = SqlSubscriptionHistoryRepository(self._db)
        self.stripe_events = SqlStripeEventRepository(self._db)
        self.roleplay_runs = SqlRoleplayRunRepository(self._db)
        self.saved_phrases = SqlSavedPhraseRepository(self._db)
        self.checkins = SqlCheckinRepository(self._db)
        self.observations = SqlObservationRepository(self._db)
        self.profiles = SqlProfileRepository(self._db)
        self.visit_sheets = SqlVisitSheetRepository(self._db)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        db = self._require()
        try:
            if exc_type is not None:
                await db.rollback()
        finally:
            await db.close()
            self._db = None

    async def commit(self) -> None:
        await self._require().commit()

    async def rollback(self) -> None:
        await self._require().rollback()

    def _require(self) -> AsyncSession:
        if self._db is None:
            raise RuntimeError("UnitOfWork used outside `async with`")
        return self._db
