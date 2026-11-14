"""Check-ins: the answer to yesterday's if-then plan, observations, and when a check-in is due."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.domain.shared.errors import DomainError

Outcome = Literal["helped", "partly", "didnt_help"]
OUTCOMES: tuple[Outcome, ...] = ("helped", "partly", "didnt_help")
ObservationSource = Literal["checkin_noted", "doctor_note"]
OBSERVATION_TEXT_MAX = 300
FOLLOW_UPS_KEY = "followUpsDidntHelp"  # value of an option's `next` that asks for the follow-ups


@dataclass(frozen=True)
class Checkin:
    """One answer per if-then plan (the plan is identified by its lesson id)."""

    session_id: UUID
    lesson_id: str
    came_up: str
    outcome: Outcome | None
    answered_at: datetime


@dataclass(frozen=True)
class Observation:
    """A family note from a check-in. Only `add_to_visit_sheet` ones are suggested on the
    visit sheet. Free text, never logged."""

    id: UUID
    session_id: UUID
    lesson_id: str
    source: ObservationSource
    text: str
    add_to_visit_sheet: bool
    created_at: datetime


def checkin_due(
    plan_created_at: datetime, app_now: datetime, timezone: str, has_checkin: bool
) -> bool:
    """Due when the plan was made on an earlier app day (session timezone) and has no check-in.
    Both times are app time (real time plus the session offset)."""
    zone = ZoneInfo(timezone)
    created_day = plan_created_at.astimezone(zone).date()
    return not has_checkin and created_day < app_now.astimezone(zone).date()


class CheckinPlanNotFound(DomainError):
    """Unknown plan id, or one that belongs to another session."""

    code = "checkin_plan_not_found"

    def __init__(self, plan_id: str) -> None:
        super().__init__("We could not find this plan.", {"planId": plan_id})


class CheckinAlreadyAnswered(DomainError):
    code = "checkin_already_answered"

    def __init__(self, plan_id: str) -> None:
        super().__init__("You already answered this check-in.", {"planId": plan_id})


class CheckinNotDue(DomainError):
    code = "checkin_not_due"

    def __init__(self, plan_id: str) -> None:
        super().__init__("This check-in opens tomorrow.", {"planId": plan_id})


class InvalidCheckinAnswer(DomainError):
    code = "invalid_checkin_answer"

    def __init__(self, reason: str, valid: list[str]) -> None:
        super().__init__(
            "That answer is not one of the choices.", {"reason": reason, "valid": valid}
        )
