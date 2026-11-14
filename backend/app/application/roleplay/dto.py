"""DTOs of the role-play use cases. None of them is ever persisted with text."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.roleplay.run import RunContext, RunMode, RunSummary
from app.domain.roleplay.verdict import CoachOutcome
from app.domain.safety.resources import CrisisResource


@dataclass(frozen=True)
class PreviousTurn:
    """An earlier round of this session, as sent by the client (max 3)."""

    parent: str
    caregiver: str
    score: int


@dataclass(frozen=True)
class CoachInput:
    """Exactly what the model gets (prompt contract): never quiz answers or visit-sheet data."""

    label: str
    variant: str | None
    round: int
    rounds_total: int
    stage: str
    parent_line: str
    parent_mood: str
    calms: tuple[str, ...]
    previous_turns: tuple[PreviousTurn, ...]
    caregiver_reply: str


@dataclass(frozen=True)
class RoundView:
    stage: str
    line: str
    mood: str


@dataclass(frozen=True)
class StartView:
    run_id: UUID
    lesson_id: str
    context: RunContext
    variant: str | None
    rounds: tuple[RoundView, ...]
    title: str
    goals: tuple[str, ...]
    intro: str | None
    labels: dict[str, str]


class TurnMode(StrEnum):
    AI = "ai"
    FALLBACK = "fallback"
    SAFETY = "safety"


class SafetyKindView(StrEnum):
    CRISIS = "crisis"
    EMERGENCY = "emergency"


@dataclass(frozen=True)
class TurnView:
    """`mode` ai: `coach` is set. fallback: `fallback_scenarios` (lesson content, rendered).
    safety: `kind` crisis (run stopped) or emergency (run paused), with `resources`."""

    mode: TurnMode
    round: int
    rounds_total: int
    coach: CoachOutcome | None = None
    kind: SafetyKindView | None = None
    resources: tuple[CrisisResource, ...] = ()
    emergency_text: str | None = None
    fallback_scenarios: tuple[dict[str, Any], ...] = ()
    run_mode: RunMode = RunMode.AI


@dataclass(frozen=True)
class TurnPhrase:
    """What the client saw for one turn, echoed back on finish (never stored)."""

    reply: str
    better_phrase: str


@dataclass(frozen=True)
class FinishView:
    run_id: UUID
    mode: RunMode
    finished_at: datetime
    summary: RunSummary
    scores: tuple[int, ...]
    first_vs_last: str | None
    best_phrase: str | None
