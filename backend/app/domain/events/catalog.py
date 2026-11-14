"""The event whitelist: names, allowed props and their value kinds.

Events are product analytics kept on our own database (no third-party trackers). The catalog is
the only place that decides what may be stored: an unknown name is an error, an unknown or
badly typed prop is dropped, and no prop can carry free text (strings must be short identifiers).
Q3-Q5 answer values are never a prop of any event.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.domain.shared.errors import DomainError

MAX_BATCH_SIZE: Final = 50
MAX_INT: Final = 100_000
_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")


class Kind(StrEnum):
    ID = "id"  # a short identifier: letters, digits, `_`, `.`, `-` (never a sentence)
    INT = "int"  # 0..MAX_INT
    BOOL = "bool"


class UnknownEvent(DomainError):
    code = "unknown_event"

    def __init__(self, name: str) -> None:
        super().__init__("This event name is not allowed.", {"name": name[:60]})


# name -> {prop: kind}. Funnel events come from content/funnel-qa.md section 5; the rest are the
# app events written by the server (and accepted from the client).
EVENT_PROPS: Final[Mapping[str, Mapping[str, Kind]]] = {
    "landing_view": {"source": Kind.ID},
    "quiz_start": {},
    "quiz_answer": {"questionId": Kind.ID},
    "quiz_back": {"questionId": Kind.ID},
    "quiz_complete": {"branch": Kind.ID},
    "plan_built": {"itemsCount": Kind.INT, "rulesVersion": Kind.ID},
    "plan_preview_view": {},
    "gift_download": {},
    "paywall_view": {"defaultPlanId": Kind.ID},
    "plan_selected": {"planId": Kind.ID},
    "consent_checked": {},
    "checkout_start": {"planId": Kind.ID},
    "checkout_success": {"planId": Kind.ID},
    "checkout_canceled": {"planId": Kind.ID},
    "demo_mode": {},
    "save_plan": {"skipped": Kind.BOOL},
    "lesson_start": {"lessonId": Kind.ID},
    "lesson_complete": {"lessonId": Kind.ID},
    "roleplay_finish": {
        "lessonId": Kind.ID,
        "context": Kind.ID,
        "mode": Kind.ID,
        "turns": Kind.INT,
        "firstScore": Kind.INT,
        "lastScore": Kind.INT,
    },
    "checkin_answer": {"planId": Kind.ID, "cameUp": Kind.ID, "outcome": Kind.ID},
    "card_published": {"phrases": Kind.INT},
    "demo_next_day": {},
    "demo_jump_to_renewal": {},
    "renewed": {"source": Kind.ID, "renewalCount": Kind.INT},
}


@dataclass(frozen=True)
class CleanEvent:
    name: str
    props: dict[str, str | int | bool]


def _valid(kind: Kind, value: object) -> bool:
    if kind is Kind.BOOL:
        return isinstance(value, bool)
    if isinstance(value, bool):
        return False
    if kind is Kind.INT:
        return isinstance(value, int) and 0 <= value <= MAX_INT
    return isinstance(value, str) and _ID_PATTERN.fullmatch(value) is not None


def clean_event(name: str, props: Mapping[str, object] | None = None) -> CleanEvent:
    """The event as it may be stored. Raises `UnknownEvent`; drops every prop that is not
    whitelisted for this event, has the wrong kind or is not a short identifier."""
    allowed = EVENT_PROPS.get(name)
    if allowed is None:
        raise UnknownEvent(name)
    kept: dict[str, str | int | bool] = {}
    for key, value in (props or {}).items():
        kind = allowed.get(key)
        if kind is not None and _valid(kind, value):
            kept[key] = value  # type: ignore[assignment]
    return CleanEvent(name, kept)
