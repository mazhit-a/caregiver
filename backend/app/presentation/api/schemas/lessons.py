"""Response schemas of the lesson routes: one per screen type.

Only fields declared here reach the client; verdicts, feedback, mini-task responses and
correctness never appear in any screen schema.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import Field, JsonValue

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


class ReviewPhraseOut(CamelModel):
    id: str
    text: str
    source: str
    lesson_id: str | None = None


class PhrasesReviewScreenOut(CamelModel):
    """`phrases` is empty when the learner has saved none: show `empty_text`."""

    id: str
    type: Literal["phrases_review"]
    title: str
    intro: str
    empty_text: str
    phrases: list[ReviewPhraseOut]


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
    | PhrasesReviewScreenOut
    | RoleplayScreenOut
    | PlanScreenOut
    | WrapScreenOut,
    Field(discriminator="type"),
]


class StepRequest(CamelModel):
    step: int = Field(ge=0, le=1000)


class LessonProgressOut(CamelModel):
    step: int
    started_at: datetime
    done_at: datetime | None


class RecapOut(CamelModel):
    from_lesson_id: str
    text: str


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
    recap: RecapOut | None = None


class AnswerRequest(CamelModel):
    """`value` is an option id for the setup, scenario and mini-task screens; other screen
    types will take structured values, so the schema accepts any JSON and the screen's handler
    decides whether the type fits."""

    screen_id: str = Field(min_length=1, max_length=64)
    value: JsonValue


class NextLessonOut(CamelModel):
    id: str
    title: str
    module_id: str
    reason: str
    unlock_on: date


class CompleteResponse(CamelModel):
    """`wrap` holds the lesson's wrap lines (the confidence check is not repeated). `nextLesson`
    is null when no later lesson is built; `allDoneLine` is then the closing text."""

    lesson_id: str
    done_at: datetime
    wrap: WrapScreenOut | None
    next_lesson: NextLessonOut | None
    all_done_line: str | None


class AnswerResponse(CamelModel):
    """`result` depends on the screen type: setup `{variant}`; scenario `{answerId, verdict,
    feedback, savePhrase}`; mini-task `{optionId, response, correct?}`; plan `{ifThen, task,
    reminder}` (reminder: title, description, startsAt, timezone, url for the browser's .ics);
    wrap `{saved, ratings}`. A plan answer value is `{response, reminderDownloaded?}`; a wrap
    answer value is `{itemId: 1..5}` for every confidence item."""

    screen_id: str
    type: str
    result: dict[str, Any]
