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


class _ScreenOut(CamelModel):
    """`part` is the small label above the screen's title."""

    id: str
    part: str | None = None


class IntroScreenOut(_ScreenOut):
    type: Literal["intro"]
    title: str
    body: str
    bullets: list[str]
    image: str | None = None


class SetupScreenOut(_ScreenOut):
    """Choosing an option always sets the lesson variant."""

    type: Literal["setup"]
    title: str
    body: str
    options: list[OptionOut]


class ScenarioAnswerOut(CamelModel):
    id: str
    text: str


class ScenarioScreenOut(_ScreenOut):
    """Verdict, feedback and button labels are not served: the answer result carries the verdict
    and feedback, the labels are in `GET /api/app-copy` (`lesson`)."""

    type: Literal["scenario"]
    title: str | None = None
    intro: str | None = None
    setup: str
    line: str
    note: str | None = None
    answers: list[ScenarioAnswerOut]


class ItemOut(CamelModel):
    title: str
    text: str


class StepOut(CamelModel):
    n: str
    title: str
    text: str


class ExampleOut(CamelModel):
    text: str
    why: str


class NoteOut(CamelModel):
    """The sticky note: two lines."""

    line1: str
    line2: str


class DoDontOut(CamelModel):
    do: list[str]
    dont: list[str]


class ContentScreenOut(_ScreenOut):
    """Teaching screen; every block but the title is optional. Client render order: body, image,
    items, steps, dodont, examples, note, keyIdea, tip."""

    type: Literal["content"]
    title: str
    body: list[str] = Field(default_factory=list)
    image: str | None = None
    items: list[ItemOut] | None = None
    steps: list[StepOut] | None = None
    dodont: DoDontOut | None = None
    examples: list[ExampleOut] | None = None
    note: NoteOut | None = None
    key_idea: str | None = None
    tip: str | None = None


class ChoiceOut(CamelModel):
    id: str
    text: str


class QuizScreenOut(_ScreenOut):
    """Options carry text only: correctness and feedback come with the answer result."""

    type: Literal["quiz"]
    title: str
    options: list[ChoiceOut]


class BuilderGroupOut(CamelModel):
    id: str
    label: str
    options: list[ChoiceOut]


class BuilderScreenOut(_ScreenOut):
    type: Literal["builder"]
    title: str
    body: str
    groups: list[BuilderGroupOut]


class ResetScreenOut(_ScreenOut):
    type: Literal["reset"]
    title: str
    body: str
    question: str
    options: list[OptionOut]
    image: str | None = None


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


class LearnScreenOut(_ScreenOut):
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


class PhrasesReviewScreenOut(_ScreenOut):
    """`phrases` is empty when the learner has saved none: show `empty_text`."""

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


class RoleplayScreenOut(_ScreenOut):
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


class PlanScreenOut(_ScreenOut):
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


class WrapScreenOut(_ScreenOut):
    type: Literal["wrap"]
    title: str | None = None
    learned: list[str] | None = None
    skill_line: str
    phrase_line: str
    pattern_line: str
    confidence_check: ConfidenceCheckOut | None = None
    tomorrow_line: str
    next_line: str


ScreenOut = Annotated[
    IntroScreenOut
    | SetupScreenOut
    | ScenarioScreenOut
    | ContentScreenOut
    | QuizScreenOut
    | BuilderScreenOut
    | ResetScreenOut
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
    screen_count: int
    progress: LessonProgressOut
    recap: RecapOut | None = None


class AnswerRequest(CamelModel):
    """`value` is an option id for the setup, scenario, quiz, reset and mini-task screens, a list
    of option ids (one per group, in order) for the builder, an object for the plan and wrap
    screens; the schema accepts any JSON and the screen's handler decides whether the type fits."""

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
    """`result` depends on the screen type:
    - setup `{variant}`;
    - scenario `{answerId, verdict, feedback, savePhrase}`;
    - quiz `{optionId, correct, correctOptionId, feedback}`;
    - builder `{reply, allCorrect, groups: [{correct}]}`;
    - reset `{optionId, text}`;
    - mini-task `{optionId, response, correct?}`;
    - plan `{ifThen, task, reminder}` (reminder: title, description, startsAt, timezone, url for
      the browser's .ics); a plan answer value is `{response, reminderDownloaded?}`;
    - wrap `{saved, ratings}`; a wrap answer value is `{itemId: 1..5}` for every confidence item.
    """

    screen_id: str
    type: str
    result: dict[str, Any]
