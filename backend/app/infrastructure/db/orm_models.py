"""SQLAlchemy ORM models. They never leave the infrastructure layer."""

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Interval,
    String,
    Text,
    Uuid,
    false,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    clock_offset: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recipient_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)


class ActiveDayRow(Base):
    __tablename__ = "active_days"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)


class LessonScheduleRow(Base):
    __tablename__ = "lesson_schedule"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    unlock_on: Mapped[date] = mapped_column(Date, nullable=False)


class QuizStateRow(Base):
    __tablename__ = "quiz_states"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_question_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    health_answers_purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PlanRow(Base):
    __tablename__ = "plans"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rules_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_version: Mapped[str] = mapped_column(String(64), nullable=False)
    lessons_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    gift_phrase_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConfidenceRow(Base):
    __tablename__ = "confidence"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    day0: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first: Mapped[dict[str, int] | None] = mapped_column(JSONB, nullable=True)
    latest: Mapped[dict[str, int] | None] = mapped_column(JSONB, nullable=True)


class IfThenPlanRow(Base):
    __tablename__ = "if_then_plans"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    cue: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    reset: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskRow(Base):
    __tablename__ = "tasks"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reminder_downloaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SubscriptionRow(Base):
    __tablename__ = "subscriptions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    renewal_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    auto_renew_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_test_clock_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    stripe_clock_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_sync: Mapped[str] = mapped_column(String(8), nullable=False, server_default="none")


class SubscriptionHistoryRow(Base):
    __tablename__ = "subscription_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    from_status: Mapped[str] = mapped_column(String(16), nullable=False)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    event: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)


class LessonProgressRow(Base):
    __tablename__ = "lesson_progress"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    screen_answers: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScenarioAnswerRow(Base):
    __tablename__ = "scenario_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64), nullable=False)
    screen_id: Mapped[str] = mapped_column(String(64), nullable=False)
    answer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SavedPhraseRow(Base):
    __tablename__ = "saved_phrases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    lesson_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StripeEventRow(Base):
    __tablename__ = "stripe_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RoleplayRunRow(Base):
    """Scores, goals, context, mode and timestamps only. No text columns, by design."""

    __tablename__ = "roleplay_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64), nullable=False)
    context: Mapped[str] = mapped_column(String(16), nullable=False)
    variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    rounds_total: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_scores: Mapped[list[int]] = mapped_column(JSONB, nullable=False, server_default="[]")
    goals_hit: Mapped[list[dict[str, bool]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CheckinRow(Base):
    """One answer per if-then plan (the plan's lesson id identifies it)."""

    __tablename__ = "checkins"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    came_up: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ObservationRow(Base):
    """A family note from a check-in; feeds the visit sheet when `add_to_visit_sheet`."""

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    add_to_visit_sheet: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VisitSheetRow(Base):
    """The doctor-visit sheet of a session (one row). Free text: never logged, never shared."""

    __tablename__ = "visit_sheets"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    doctor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    family_notes: Mapped[str] = mapped_column(String(2000), nullable=False, server_default="")
    questions: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProfileRow(Base):
    """The non-medical profile; the display name stays in `sessions.display_name`."""

    __tablename__ = "profiles"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    enjoys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    calms: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    avoid: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    rhythm: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    contacts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    caregiver_first_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CareCardRow(Base):
    """A published care card or its tombstone (`snapshot` NULL, `revoked_at` set). Several rows
    per session are possible (a revoked id stays a tombstone after a republish)."""

    __tablename__ = "care_cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    phrase_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
