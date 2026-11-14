"""What the plan and wrap screens save: the if-then plan, the do-now task, confidence ratings."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

IF_THEN_RESPONSE_MAX = 300
CONFIDENCE_MIN = 1
CONFIDENCE_MAX = 5
REMINDER_HOUR = 19  # "evening" for the reminder: 19:00 in the session timezone


@dataclass(frozen=True)
class IfThenPlan:
    """The learner's own plan: cue (from the variant), their words, and the reset they chose.
    One per lesson; answering again replaces it."""

    session_id: UUID
    lesson_id: str
    cue: str
    response: str
    reset: str | None
    created_at: datetime


@dataclass(frozen=True)
class Task:
    """The "one thing to do now" of a lesson. `reminder_downloaded` is reported by the browser;
    `done_at` is set later by check-ins."""

    session_id: UUID
    lesson_id: str
    text: str
    action: str
    reminder_downloaded: bool
    created_at: datetime
    done_at: datetime | None = None


@dataclass(frozen=True)
class ConfidenceRatings:
    """Slider ratings by item id: from the first lesson's check and from the latest later one."""

    first: dict[str, int] | None = None
    latest: dict[str, int] | None = None


def next_evening(app_now: datetime, timezone: str) -> datetime:
    """The next 19:00 in the session timezone: today's if it is still ahead, else tomorrow's."""
    zone = ZoneInfo(timezone)
    local = app_now.astimezone(zone)
    candidate = datetime.combine(local.date(), time(REMINDER_HOUR), tzinfo=zone)
    if candidate <= local:
        candidate = datetime.combine(
            local.date() + timedelta(days=1), time(REMINDER_HOUR), tzinfo=zone
        )
    return candidate
