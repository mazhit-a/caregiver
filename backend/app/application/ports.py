"""Ports (Protocols) that infrastructure adapters implement."""

from collections.abc import Mapping
from datetime import date, datetime
from types import TracebackType
from typing import Any, Literal, Protocol, Self
from uuid import UUID

from app.application.billing.events import BillingEvent
from app.application.billing.payments import (
    CheckoutRequest,
    CheckoutSessionInfo,
    CheckoutSessionRef,
    CustomerRef,
)
from app.application.roleplay.dto import CoachInput
from app.domain.billing.entities import Subscription, SubscriptionHistoryEntry
from app.domain.billing.pricing import Pricing
from app.domain.care_card.entities import CareCard
from app.domain.lessons.plans import ConfidenceRatings, IfThenPlan, Task
from app.domain.lessons.progress import LessonProgress, ScenarioAnswer
from app.domain.phrases.entities import SavedPhrase
from app.domain.plan.entities import PhraseSheetText, PhraseText, PlanRules, StoredPlan
from app.domain.profile.entities import Profile
from app.domain.quiz.definition import QuizDefinition
from app.domain.quiz.entities import QuizState
from app.domain.roleplay.run import RunRecord
from app.domain.roleplay.verdict import CoachTips, CoachVerdict
from app.domain.safety.check import SafetyTerms
from app.domain.safety.resources import CrisisResource
from app.domain.schedule.entities import ScheduledLesson
from app.domain.session.entities import Session
from app.domain.shared.errors import DomainError
from app.domain.shared.labels import RecipientLabels
from app.domain.today.checkins import Checkin, Observation
from app.domain.visit_sheet.entities import VisitQuestionBank, VisitSheet


class Clock(Protocol):
    """Source of app time (real now plus session offset). Never call datetime.now() elsewhere."""

    def now(self) -> datetime: ...


class SessionRepository(Protocol):
    async def add(self, session: Session) -> None: ...

    async def get_by_token_hash(self, token_hash: str) -> Session | None: ...

    async def get(self, session_id: UUID) -> Session | None: ...

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


class LessonProgressRepository(Protocol):
    async def get(self, session_id: UUID, lesson_id: str) -> LessonProgress | None: ...

    async def save(self, progress: LessonProgress) -> None:
        """Insert or update the progress row of the lesson."""
        ...

    async def list_for_session(self, session_id: UUID) -> list[LessonProgress]:
        """The progress rows of every lesson the session has started."""
        ...


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


class ScenarioAnswerRepository(Protocol):
    async def add(self, answer: ScenarioAnswer) -> None:
        """Record one scenario pick; retries add rows."""
        ...

    async def list_for_lesson(self, session_id: UUID, lesson_id: str) -> list[ScenarioAnswer]:
        """The picks of the lesson, oldest first."""
        ...

    async def list_for_session(self, session_id: UUID) -> list[ScenarioAnswer]:
        """Every pick of the session, oldest first."""
        ...


class ConfidenceRepository(Protocol):
    async def get_day0(self, session_id: UUID) -> int | None: ...

    async def save_day0(self, session_id: UUID, value: int) -> None:
        """Insert or update `day0` (the Q11 answer) without touching later columns."""
        ...

    async def get_ratings(self, session_id: UUID) -> ConfidenceRatings: ...

    async def save_ratings(
        self, session_id: UUID, slot: Literal["first", "latest"], ratings: dict[str, int]
    ) -> None:
        """Insert or update the `first` or `latest` slider ratings, keeping the other columns."""
        ...


class IfThenPlanRepository(Protocol):
    async def get(self, session_id: UUID, lesson_id: str) -> IfThenPlan | None: ...

    async def save(self, plan: IfThenPlan) -> None:
        """Insert or replace the if-then plan of the lesson."""
        ...

    async def latest(self, session_id: UUID) -> IfThenPlan | None:
        """The most recently created plan of the session."""
        ...


class TaskRepository(Protocol):
    async def get(self, session_id: UUID, lesson_id: str) -> Task | None: ...

    async def save(self, task: Task) -> None:
        """Insert or replace the do-now task of the lesson (`done_at` is kept)."""
        ...

    async def mark_done(self, session_id: UUID, lesson_id: str, done_at: datetime) -> None:
        """Set `done_at` of the task (a check-in said it helped); no-op when there is no task."""
        ...

    async def list_for_session(self, session_id: UUID) -> list[Task]: ...


class CheckinRepository(Protocol):
    async def get(self, session_id: UUID, lesson_id: str) -> Checkin | None: ...

    async def add(self, checkin: Checkin) -> None: ...

    async def list_for_session(self, session_id: UUID) -> list[Checkin]:
        """Oldest first."""
        ...


class ObservationRepository(Protocol):
    async def add(self, observation: Observation) -> None: ...

    async def list_for_session(self, session_id: UUID) -> list[Observation]:
        """Oldest first."""
        ...


class VisitSheetRepository(Protocol):
    async def get(self, session_id: UUID) -> VisitSheet | None: ...

    async def save(self, sheet: VisitSheet) -> None:
        """Insert or replace the one sheet of the session."""
        ...


class SubscriptionRepository(Protocol):
    async def get(self, session_id: UUID) -> Subscription | None: ...

    async def get_by_stripe_customer_id(self, customer_id: str) -> Subscription | None: ...

    async def save(self, subscription: Subscription) -> None:
        """Insert or update the subscription row of the session (history is separate)."""
        ...


class SubscriptionHistoryRepository(Protocol):
    async def add(self, entry: SubscriptionHistoryEntry) -> None: ...

    async def list_for_session(self, session_id: UUID) -> list[SubscriptionHistoryEntry]:
        """All entries of the session, oldest first."""
        ...


class StripeEventRepository(Protocol):
    """Processed webhook events, keyed by the provider's event id (idempotency)."""

    async def begin(self, event_id: str, event_type: str, received_at: datetime) -> bool:
        """Record the event before it is handled. True when it must be processed: a new event,
        or one recorded earlier whose processing never finished. False for a processed duplicate."""
        ...

    async def mark_processed(self, event_id: str, processed_at: datetime) -> None: ...


class SavedPhraseRepository(Protocol):
    async def add(self, phrase: SavedPhrase) -> None: ...

    async def count(self, session_id: UUID) -> int: ...

    async def list_for_session(self, session_id: UUID) -> list[SavedPhrase]:
        """The session's phrases, oldest first."""
        ...

    async def delete(self, session_id: UUID, phrase_id: UUID) -> bool:
        """Delete the phrase when it belongs to the session; False when there is no such row."""
        ...


class ProfileRepository(Protocol):
    async def get(self, session_id: UUID) -> Profile | None: ...

    async def save(self, profile: Profile) -> None:
        """Insert or replace the session's profile."""
        ...


class CareCardRepository(Protocol):
    async def get(self, card_id: str) -> CareCard | None:
        """Any card row by public id, live or tombstone."""
        ...

    async def get_current(self, session_id: UUID) -> CareCard | None:
        """The session's live card, else its most recently revoked tombstone, else None."""
        ...

    async def save(self, card: CareCard) -> None:
        """Insert or replace the row with this id."""
        ...


class RoleplayRunRepository(Protocol):
    async def get(self, run_id: UUID) -> RunRecord | None: ...

    async def save(self, record: RunRecord) -> None:
        """Insert or update the run (scores, goals, mode, finished_at; never any text)."""
        ...

    async def list_finished(self, session_id: UUID) -> list[RunRecord]:
        """The session's finished runs, oldest `finished_at` first."""
        ...


class UnitOfWork(Protocol):
    """Transaction boundary: `async with uow:` ... `await uow.commit()`.

    Repositories are attributes of the unit of work; they never commit themselves.
    """

    sessions: SessionRepository
    active_days: ActiveDayRepository
    quiz: QuizStateRepository
    lesson_schedule: LessonScheduleRepository
    lesson_progress: LessonProgressRepository
    scenario_answers: ScenarioAnswerRepository
    plans: PlanRepository
    confidence: ConfidenceRepository
    if_then_plans: IfThenPlanRepository
    tasks: TaskRepository
    subscriptions: SubscriptionRepository
    subscription_history: SubscriptionHistoryRepository
    stripe_events: StripeEventRepository
    roleplay_runs: RoleplayRunRepository
    saved_phrases: SavedPhraseRepository
    checkins: CheckinRepository
    observations: ObservationRepository
    profiles: ProfileRepository
    visit_sheets: VisitSheetRepository
    care_cards: CareCardRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class CoachUnavailable(DomainError):
    """The only failure a `Coach` raises: timeout, API error, refusal or invalid JSON."""

    code = "coach_unavailable"


class Coach(Protocol):
    """The role-play coach (LLM). One call per caregiver reply; never decides scores."""

    async def turn(self, coach_input: CoachInput) -> CoachVerdict:
        """The model's judgement of the reply. Raises `CoachUnavailable` on any failure."""
        ...


class RateLimiter(Protocol):
    async def allow(self, key: str, now: datetime) -> bool:
        """Record one hit for `key` and say whether it is within the limit."""
        ...


class PaymentGateway(Protocol):
    """Payments adapter (Stripe). Every provider failure is raised as `PaymentGatewayError`."""

    async def create_customer(self, session_id: UUID, clock_frozen_at: datetime) -> CustomerRef:
        """Create a customer on a new Test Clock frozen at `clock_frozen_at` (the app time)."""
        ...

    async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSessionRef:
        """A subscription Checkout Session: the plan's renewal price plus the intro coupon."""
        ...

    async def retrieve_checkout_session(self, checkout_id: str) -> CheckoutSessionInfo: ...

    async def cancel_at_period_end(self, subscription_id: str) -> None: ...

    async def cancel_now(self, subscription_id: str) -> None: ...

    async def advance_test_clock(self, test_clock_id: str, to: datetime) -> None:
        """Move a Stripe Test Clock forward to `to` (never backward)."""
        ...

    async def attach_failing_payment_method(self, customer_id: str) -> None:
        """Make the customer's next charge fail (test card that is declined)."""
        ...


class WebhookParser(Protocol):
    """Verifies a provider webhook and turns it into a `BillingEvent`.

    Raises `InvalidWebhookSignature` for a missing or wrong signature.
    """

    def parse(self, payload: bytes, signature: str | None) -> BillingEvent: ...


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

    def lesson_recipient_labels(self, key: str, display_name: str | None = None) -> RecipientLabels:
        """Labels for lesson text (`both` becomes the singular "your parent"); a display name
        replaces `{recipient}` / `{possessive}`."""
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
        display_name: str | None = None,
    ) -> dict[str, Any]: ...

    def pricing(self) -> Pricing:
        """The plans of pricing.json with the disclosure values the paywall needs."""
        ...

    def crisis_resources(self) -> list[CrisisResource]: ...

    def visit_questions(self) -> VisitQuestionBank:
        """The doctor-visit question bank and the footer that is always shown."""
        ...

    def safety_terms(self) -> SafetyTerms:
        """Crisis and emergency terms and excluded phrases for the local safety check."""
        ...

    def coach_tips(self) -> CoachTips:
        """The fixed coach tips (medical, off topic, too short); `{label}` still unfilled."""
        ...

    def crisis_resources_need_verification(self) -> bool:
        """True while the phone numbers are still marked "to be verified before launch"."""
        ...
