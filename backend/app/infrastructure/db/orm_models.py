"""SQLAlchemy ORM models. They never leave the infrastructure layer."""

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import (
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
    day0: Mapped[int] = mapped_column(Integer, nullable=False)
