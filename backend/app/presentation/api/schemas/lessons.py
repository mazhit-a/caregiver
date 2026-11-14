"""Response schemas of the lesson routes: one per screen type.

Only fields declared here reach the client; verdicts, feedback, mini-task responses and
correctness never appear in any screen schema.
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field

from app.presentation.api.schemas.base import CamelModel


class OptionOut(CamelModel):
    id: str
    label: str


class SetupQuestionScreenOut(CamelModel):
    id: str
    type: Literal["setup_question"]
    speaker: str
    text: str
    question: str
    options: list[OptionOut]


class ScenarioAnswerOut(CamelModel):
    id: str
    text: str


class ScenarioScreenOut(CamelModel):
    id: str
    type: Literal["scenario"]
    intro: str | None = None
    setup: str
    line: str
    question: str
    answers: list[ScenarioAnswerOut]
    verdict_labels: dict[str, str]
    after_choice: str
    save_button: str


class PatternStepOut(CamelModel):
    id: str
    label: str
    example: str


class PatternOut(CamelModel):
    name: str
    steps: list[PatternStepOut]


class MiniTaskOut(CamelModel):
    question: str
    options: list[OptionOut]


class LearnScreenOut(CamelModel):
    id: str
    type: Literal["learn"]
    title: str
    body: str | None = None
    bullets: list[str] | None = None
    extra: str | None = None
    pattern_tip: str | None = None
    pattern: PatternOut | None = None
    mini_task: MiniTaskOut | None = None


class RoundOut(CamelModel):
    stage: str
    line: str
    mood: str


class RoleplayLabelsOut(CamelModel):
    partner: str
    not_saved: str
    thinking: str
    ai_down: str


class RoleplaySummaryOut(CamelModel):
    title: str
    best_phrase_label: str
    save_button: str
    again_button: str


class RoleplayScreenOut(CamelModel):
    id: str
    type: Literal["roleplay"]
    title: str
    intro: str
    goals: list[str]
    rounds: list[RoundOut]
    labels: RoleplayLabelsOut
    summary: RoleplaySummaryOut


class IfThenOut(CamelModel):
    cue: str
    response_label: str
    response_editable: bool
    reset_label: str
    reset_from: str


class DoNowOut(CamelModel):
    title: str
    text: str
    action: str
    button: str


class NoteTemplateOut(CamelModel):
    title: str
    example: str


class PlanScreenOut(CamelModel):
    id: str
    type: Literal["plan"]
    title: str
    if_then: IfThenOut
    do_now: DoNowOut
    remind_button: str
    done_button: str
    note_template: NoteTemplateOut


class ConfidenceCheckOut(CamelModel):
    title: str
    scale: str
    items: list[OptionOut]


class WrapScreenOut(CamelModel):
    id: str
    type: Literal["wrap"]
    skill_line: str
    phrase_line: str
    pattern_line: str
    confidence_check: ConfidenceCheckOut | None = None
    tomorrow_line: str
    next_line: str


ScreenOut = Annotated[
    SetupQuestionScreenOut
    | ScenarioScreenOut
    | LearnScreenOut
    | RoleplayScreenOut
    | PlanScreenOut
    | WrapScreenOut,
    Field(discriminator="type"),
]


class LessonProgressOut(CamelModel):
    step: int
    started_at: datetime
    done_at: datetime | None


class LessonResponse(CamelModel):
    id: str
    module_id: str
    title: str
    minutes: int
    skill: str
    skill_label: str
    variant: str | None
    unlock_on: date
    pattern: PatternOut
    screens: list[ScreenOut]
    progress: LessonProgressOut
