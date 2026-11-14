"""Ports (Protocols) that infrastructure adapters implement."""

from collections.abc import Mapping
from datetime import date, datetime
from types import TracebackType
from typing import Any, Protocol, Self
from uuid import UUID

from app.domain.billing.entities import Subscription, SubscriptionHistoryEntry
from app.domain.billing.pricing import Pricing
from app.domain.plan.entities import PhraseSheetText, PhraseText, PlanRules, StoredPlan
from app.domain.quiz.definition import QuizDefinition
from app.domain.quiz.entities import QuizState
from app.domain.safety.resources import CrisisResource
from app.domain.schedule.entities import ScheduledLesson
from app.domain.session.entities import Session
from app.domain.shared.labels import RecipientLabels


class Clock(Protocol):
    """Source of app time (real now plus session offset). Never call datetime.now() elsewhere."""

    def now(self) -> datetime: ...


class SessionRepository(Protocol):
    async def add(self, session: Session) -> None: ...

    async def get_by_token_hash(self, token_hash: str) -> Session | None: ...

    async def save(self, session: Session) -> None:
        """Persist the mutable fields (offset, last_seen_at, recipient_key, display_name)."""
        ...


class ActiveDayRepository(Protocol):
    async def record(self, session_id: UUID, day: date) -> bool:
        """Record an active app day once; True when newly recorded, False if already there."""
        ...

    async def list_days(self, session_id: UUID) -> list[date]: ...


class LessonScheduleRepository(Protocol):
    async def list_for_session(self, session_id: UUID) -> list[ScheduledLesson]:
        """All scheduled lessons of the session, ordered by seq."""
        ...

    async def add_many(self, session_id: UUID, lessons: list[ScheduledLesson]) -> None: ...


class QuizStateRepository(Protocol):
    async def get(self, session_id: UUID) -> QuizState | None: ...

    async def save(self, state: QuizState) -> None:
        """Insert or update the quiz state of the session."""
        ...


class PlanRepository(Protocol):
    async def get(self, session_id: UUID) -> StoredPlan | None: ...

    async def save(self, plan: StoredPlan) -> None:
        """Insert or replace the plan snapshot of the session."""
        ...


class ConfidenceRepository(Protocol):
    async def get_day0(self, session_id: UUID) -> int | None: ...

    async def save_day0(self, session_id: UUID, value: int) -> None:
        """Insert or update `day0` (the Q11 answer) without touching later columns."""
        ...


class SubscriptionRepository(Protocol):
    async def get(self, session_id: UUID) -> Subscription | None: ...

    async def save(self, subscription: Subscription) -> None:
        """Insert or update the subscription row of the session (history is separate)."""
        ...


class SubscriptionHistoryRepository(Protocol):
    async def add(self, entry: SubscriptionHistoryEntry) -> None: ...

    async def list_for_session(self, session_id: UUID) -> list[SubscriptionHistoryEntry]:
        """All entries of the session, oldest first."""
        ...


class UnitOfWork(Protocol):
    """Transaction boundary: `async with uow:` ... `await uow.commit()`.

    Repositories are attributes of the unit of work; they never commit themselves.
    """

    sessions: SessionRepository
    active_days: ActiveDayRepository
    quiz: QuizStateRepository
    lesson_schedule: LessonScheduleRepository
    plans: PlanRepository
    confidence: ConfidenceRepository
    subscriptions: SubscriptionRepository
    subscription_history: SubscriptionHistoryRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TokenGenerator(Protocol):
    """Generates public, unguessable tokens (session tokens, card ids)."""

    def new_token(self) -> str: ...


class IdGenerator(Protocol):
    """Generates internal row ids (UUIDs) so that domain and use cases never call uuid4."""

    def new_id(self) -> UUID: ...


class ContentProvider(Protocol):
    """Read access to validated content. Text is returned with placeholders already filled."""

    @property
    def content_version(self) -> str: ...

    def recipient_keys(self) -> list[str]: ...

    def recipient_labels(self, key: str) -> RecipientLabels:
        """Quiz labels for a Q1 key (`both` is plural: "your parents")."""
        ...

    def lesson_recipient_labels(self, key: str) -> RecipientLabels:
        """Labels for lesson text (`both` becomes the singular "your parent")."""
        ...

    def quiz_definition(self) -> QuizDefinition:
        """The quiz questions as the quiz domain reads them (placeholders still unfilled)."""
        ...

    def plan_rules(self) -> PlanRules:
        """The plan rules (plan-rules.json plus the phrase tags) as the plan builder reads them."""
        ...

    def phrase_sheet(self) -> PhraseSheetText:
        """Title, intro and footer of the gift phrase sheet (placeholders unfilled)."""
        ...

    def phrases(self) -> list[PhraseText]:
        """The phrase bank in list order (placeholders unfilled)."""
        ...

    def lesson_ids(self) -> list[str]: ...

    def lesson_variants(self, lesson_id: str) -> list[str]: ...

    def render_lesson(
        self,
        lesson_id: str,
        recipient_key: str,
        variant: str | None = None,
        runtime_values: Mapping[str, str] | None = None,
    ) -> dict[str, Any]: ...

    def pricing(self) -> Pricing:
        """The plans of pricing.json with the disclosure values the paywall needs."""
        ...

    def crisis_resources(self) -> list[CrisisResource]: ...

    def crisis_resources_need_verification(self) -> bool:
        """True while the phone numbers are still marked "to be verified before launch"."""
        ...
