"""Role-play request and response schemas.

Request size limits are the first line of defence for the model prompt: every client-sent
string is capped here (the reply at 150 characters, at most 3 previous turns).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.application.roleplay.dto import FinishView, StartView, TurnMode, TurnView
from app.domain.roleplay.run import RunContext, RunMode
from app.domain.roleplay.verdict import CoachOutcome
from app.presentation.api.schemas.base import CamelModel

MAX_REPLY = 150
MAX_PREVIOUS_TURNS = 3
MAX_LINE = 400  # a parent line or an earlier better phrase
MAX_ROUNDS = 10


class StartRequest(CamelModel):
    lesson_id: str = Field(min_length=1, max_length=64)
    context: RunContext = RunContext.LESSON


class PreviousTurnIn(CamelModel):
    parent: str = Field(min_length=1, max_length=MAX_LINE)
    caregiver: str = Field(min_length=1, max_length=MAX_REPLY)
    score: int = Field(ge=0, le=3)


class TurnRequest(CamelModel):
    round: int = Field(ge=1, le=MAX_ROUNDS)
    reply: str = Field(min_length=1, max_length=MAX_REPLY)
    previous_turns: list[PreviousTurnIn] = Field(
        default_factory=list, max_length=MAX_PREVIOUS_TURNS
    )


class TurnPhraseIn(CamelModel):
    reply: str = Field(min_length=1, max_length=MAX_REPLY)
    better_phrase: str = Field(max_length=MAX_LINE)


class FinishRequest(CamelModel):
    phrases: list[TurnPhraseIn] = Field(default_factory=list, max_length=MAX_ROUNDS)


class RoundOut(CamelModel):
    stage: str
    line: str
    mood: str


class StartResponse(CamelModel):
    run_id: UUID
    lesson_id: str
    context: RunContext
    variant: str | None
    rounds_total: int
    rounds: list[RoundOut]
    title: str
    goals: list[str]
    intro: str | None
    labels: dict[str, str]


class GoalsOut(CamelModel):
    notice: bool
    reassure: bool
    offer: bool


class CoachOut(CamelModel):
    """The coach panel. Every text field here is model output: `ai_generated` is always true
    so the client labels it as AI-generated."""

    ai_generated: Literal[True] = True
    score: int
    goals: GoalsOut
    argued: bool
    flags: list[str]
    tip: str
    better_phrase: str
    parent_reaction: str
    parent_mood: str


class ResourceOut(CamelModel):
    id: str
    name: str
    phone: str
    description: str


class TurnResponse(CamelModel):
    """`mode` ai: `coach` is set. fallback: `fallbackScenarios` (lesson content, the multiple
    choice scenarios to show instead). safety: `kind` crisis | emergency with `resources`."""

    mode: TurnMode
    run_mode: RunMode
    round: int
    rounds_total: int
    coach: CoachOut | None = None
    kind: Literal["crisis", "emergency"] | None = None
    resources: list[ResourceOut] = Field(default_factory=list)
    emergency_text: str | None = None
    fallback_scenarios: list[dict[str, object]] = Field(default_factory=list)


class SummaryOut(CamelModel):
    first_score: int | None
    last_score: int | None
    improved: bool
    notice_turns: int
    reassure_turns: int
    offer_turns: int


class FinishResponse(CamelModel):
    run_id: UUID
    mode: RunMode
    finished_at: datetime
    summary: SummaryOut
    scores: list[int]
    first_vs_last: str | None
    best_phrase: str | None


def start_response(view: StartView) -> StartResponse:
    return StartResponse(
        run_id=view.run_id,
        lesson_id=view.lesson_id,
        context=view.context,
        variant=view.variant,
        rounds_total=len(view.rounds),
        rounds=[RoundOut(stage=r.stage, line=r.line, mood=r.mood) for r in view.rounds],
        title=view.title,
        goals=list(view.goals),
        intro=view.intro,
        labels=view.labels,
    )


def _coach_out(outcome: CoachOutcome) -> CoachOut:
    return CoachOut(
        score=outcome.score,
        goals=GoalsOut(
            notice=outcome.goals.notice,
            reassure=outcome.goals.reassure,
            offer=outcome.goals.offer,
        ),
        argued=outcome.argued,
        flags=list(outcome.flags),
        tip=outcome.tip,
        better_phrase=outcome.better_phrase,
        parent_reaction=outcome.parent_reaction,
        parent_mood=outcome.parent_mood,
    )


def turn_response(view: TurnView) -> TurnResponse:
    return TurnResponse(
        mode=view.mode,
        run_mode=view.run_mode,
        round=view.round,
        rounds_total=view.rounds_total,
        coach=_coach_out(view.coach) if view.coach is not None else None,
        kind=view.kind.value if view.kind is not None else None,
        resources=[
            ResourceOut(id=r.id, name=r.name, phone=r.phone, description=r.description)
            for r in view.resources
        ],
        emergency_text=view.emergency_text,
        fallback_scenarios=[dict(s) for s in view.fallback_scenarios],
    )


def finish_response(view: FinishView) -> FinishResponse:
    s = view.summary
    return FinishResponse(
        run_id=view.run_id,
        mode=view.mode,
        finished_at=view.finished_at,
        summary=SummaryOut(
            first_score=s.first_score,
            last_score=s.last_score,
            improved=s.improved,
            notice_turns=s.notice_turns,
            reassure_turns=s.reassure_turns,
            offer_turns=s.offer_turns,
        ),
        scores=list(view.scores),
        first_vs_last=view.first_vs_last,
        best_phrase=view.best_phrase,
    )
