"""Pydantic models of the content files. Unknown fields fail validation on purpose."""

import re
from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class ContentModel(BaseModel):
    """Base: camelCase aliases like the JSON files, immutable, no unknown fields."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


class Notes(ContentModel):
    notes: list[str] = []


# ---------------------------------------------------------------- quiz.json


class RecipientLabelsModel(ContentModel):
    recipient: str
    possessive: str
    pronoun: str
    object: str
    was: str
    is_: str = Field(alias="is")
    has: str
    lives: str


class Branch(ContentModel):
    label: str


class Heard(ContentModel):
    slot: str
    text: str


class QuizOption(ContentModel):
    id: str
    label: str
    tags: list[str]
    heard: Heard | None = None
    branch: str | None = None
    exclusive: bool | None = None


class SingleQuestion(ContentModel):
    id: str
    type: Literal["single"]
    title: str
    subtitle: str | None = None
    used_for: str
    health_data: bool | None = None
    options: list[QuizOption]


class MultiQuestion(ContentModel):
    id: str
    type: Literal["multi"]
    title: str
    subtitle: str | None = None
    subtitle_by_branch: dict[str, str] | None = None
    used_for: str
    health_data: bool | None = None
    skippable: bool | None = None
    max: int
    options: list[QuizOption]


class InterstitialQuestion(ContentModel):
    id: str
    type: Literal["interstitial"]
    speaker: str
    title: str
    body: str
    cta: str


class GridState(ContentModel):
    id: str
    label: str


class GridRow(ContentModel):
    id: str
    label: str
    hint: str


class DerivedTag(ContentModel):
    if_: str = Field(alias="if")
    add: str


class GridQuestion(ContentModel):
    id: str
    type: Literal["grid"]
    title: str
    subtitle: str | None = None
    used_for: str
    states: list[GridState]
    rows: list[GridRow]
    derived_tags: list[DerivedTag]


class ScaleQuestion(ContentModel):
    id: str
    type: Literal["scale"]
    title: str
    used_for: str
    min: int
    max: int
    min_label: str
    max_label: str
    store_as: str
    derived_tags: list[DerivedTag]


QuizQuestion = Annotated[
    SingleQuestion | MultiQuestion | InterstitialQuestion | GridQuestion | ScaleQuestion,
    Field(discriminator="type"),
]


class QuizFile(Notes):
    version: int
    recipient_labels: dict[str, RecipientLabelsModel]
    branches: dict[str, Branch]
    questions: list[QuizQuestion]


# ---------------------------------------------------------------- plan-rules.json


class RuleLesson(ContentModel):
    id: str
    title: str
    minutes: int
    built: bool
    build_next: bool | None = None
    review: bool | None = None
    handout: str | None = None


class RuleModule(ContentModel):
    id: str
    title: str
    order: Literal["first", "noticing_second", "scored", "later"]
    skill: str
    summary: str | None = None
    reason: str | None = None
    base_score: int | None = None
    lessons: list[RuleLesson]


class FirstModule(ContentModel):
    id: str
    reason_by_branch: dict[str, str]


class Boost(ContentModel):
    all: list[str] = []
    any: list[str] | None = None
    none: list[str] | None = None
    module: str
    points: int
    reason: str


class QuickGuide(ContentModel):
    id: str
    title: str
    highlight_if: list[str]


class UnlockRule(ContentModel):
    """Parameters of `ceil(k * days_per_week / lessons_per_week) + first_lesson_offset_days`."""

    formula: str
    days_per_week: int = Field(gt=0)
    first_lesson_offset_days: int = Field(ge=0)


class Pace(ContentModel):
    lessons_per_week: dict[str, int]
    label: str
    unlock_rule: UnlockRule


class HeardSentence(ContentModel):
    slots: list[str]
    prefix: str | None = None
    join: str | None = None
    list_join: str | None = None
    last_join: str | None = None
    end: str | None = None


class WhatWeHeardRules(ContentModel):
    title: str
    sentences: list[HeardSentence]
    rules: list[str]
    example: str


class BeforeAfter(ContentModel):
    before: str
    after: str


class LoaderLine(ContentModel):
    text: str
    always: bool | None = None
    any: list[str] | None = None


class GiftPhrases(ContentModel):
    count: int
    rule: str


class Readiness(ContentModel):
    description: str


class PlanRulesFile(Notes):
    version: int
    algorithm: list[str]
    first_module: FirstModule
    first_lesson_id: str
    modules: list[RuleModule]
    boosts: list[Boost]
    quick_guides: list[QuickGuide]
    quick_guides_note: str
    pace: Pace
    skills: dict[str, str]
    plan_intro: dict[str, str]
    what_we_heard: WhatWeHeardRules
    before_after: dict[str, BeforeAfter]
    loader_lines: list[LoaderLine]
    loader_rules: str
    gift_phrases: GiftPhrases
    readiness: Readiness


# ---------------------------------------------------------------- phrases.json


class Phrase(ContentModel):
    id: str
    tags: list[str]
    text: str
    when: str


class PhraseSheet(ContentModel):
    title: str
    intro: str
    footer: str


class PhrasesFile(Notes):
    version: int
    sheet: PhraseSheet
    phrases: list[Phrase]


# ---------------------------------------------------------------- pricing.json


class PricingPlan(ContentModel):
    id: str
    label: str
    intro_price: float
    intro_days: int
    intro_period_text: str
    renew_price: float
    renew_days: int
    renew_period_text: str
    stripe_intro_price_id: str
    stripe_renew_price_id: str
    stripe_intro_coupon_id: str
    status: str


class PricingFile(Notes):
    version: int
    currency: str
    default_plan_id: str
    plans: list[PricingPlan]


# ---------------------------------------------------------------- safety-terms.json


class SafetyMatching(ContentModel):
    mode: Literal["whole_word"]
    case_insensitive: bool
    excluded_phrases: list[str] = []


class CoachTipsModel(ContentModel):
    medical: str
    off_topic: str
    too_short: str


class SafetyTermsFile(Notes):
    version: int
    matching: SafetyMatching
    coach_tips: CoachTipsModel
    crisis: list[str] = Field(min_length=1)
    emergency: list[str] = Field(min_length=1)
    medical: list[str] = Field(min_length=1)


# ---------------------------------------------------------------- crisis-resources.json


class CrisisResourceModel(ContentModel):
    id: str
    name: str
    phone: str
    description: str


class CrisisResourcesFile(Notes):
    version: int
    verify_before_launch: bool
    resources: list[CrisisResourceModel] = Field(min_length=1)


# ---------------------------------------------------------------- visit-questions.json


class VisitQuestion(ContentModel):
    id: str
    text: str


class VisitQuestionsFile(Notes):
    version: int
    footer: str
    questions: list[VisitQuestion] = Field(min_length=1)


# ---------------------------------------------------------------- funnel-copy.json


class TitleBody(ContentModel):
    title: str
    body: str


class Hero(ContentModel):
    title: str
    subtitle: str
    cta: str
    cta_note: str


class DemoExchange(ContentModel):
    title: str
    mom_line: str
    your_line: str
    coach_tip: str


class Faq(ContentModel):
    q: str
    a: str


class Landing(ContentModel):
    hero: Hero
    blocks: list[TitleBody]
    demo: DemoExchange
    trust: list[str]
    faq: list[Faq]
    footer: str


class QuizIntro(ContentModel):
    title: str
    body: str
    cta: str


class QuizCopy(ContentModel):
    health_note: str


class Loader(ContentModel):
    title: str
    line_source_note: str
    duration_ms: int


class PreviewWhatWeHeard(ContentModel):
    title: str
    edit_link: str


class PreviewBeforeAfter(ContentModel):
    title: str
    before_label: str
    after_label: str


class PreviewPlan(ContentModel):
    title: str
    first30_title: str
    module_lessons_label: str
    first_lesson_badge: str
    current_module_badge: str
    later_title: str
    locked_hint: str
    reason_prefix: str
    pace_line: str
    quick_guides_title: str
    quick_guides_note: str
    highlight_label: str


class ProofItem(ContentModel):
    text: str
    source: str


class Proof(ContentModel):
    title: str
    items: list[ProofItem]


class Gift(ContentModel):
    title: str
    body: str
    cta: str
    note: str


class PlanPreview(ContentModel):
    title: str
    what_we_heard: PreviewWhatWeHeard
    before_after: PreviewBeforeAfter
    plan: PreviewPlan
    proof: Proof
    gift: Gift
    cta: str


class PaywallStates(ContentModel):
    loading: str
    card_error: str
    success: str
    returned_canceled: str


class Paywall(ContentModel):
    headline: str
    subhead_from_summary: str
    includes_title: str
    includes: list[str]
    plan_labels: dict[str, str]
    selected_badge_note: str
    money_format: str
    plan_detail: str
    disclosure: str
    consent_checkbox: str
    consent_required_error: str
    pay_button: str
    test_mode_hint: str
    demo_button: str
    demo_note: str
    footer: str
    states: PaywallStates


class TodaySubscriptionCopy(ContentModel):
    renews_on: str
    renewed: str
    ends_on: str


class TodayWelcomeBackCopy(ContentModel):
    title: str
    body: str


class TodayDemoControl(ContentModel):
    id: str
    label: str


class TodayDemoCopy(ContentModel):
    label: str
    controls: list[TodayDemoControl]


class TodayCopyFile(ContentModel):
    title: str
    rest_message: str
    all_built_done: str
    next_unlock: str
    care_card_nudge_one: str
    care_card_nudge_many: str
    weekly_rhythm: str
    readiness: str
    subscription: TodaySubscriptionCopy
    welcome_back: TodayWelcomeBackCopy
    visit_sheet_link: str
    demo: TodayDemoCopy
    welcome_back_after_days: int = Field(ge=1)
    renewed_notice_days: int = Field(ge=1)


class GentleExitResource(ContentModel):
    id: str
    name: str
    description: str
    phone: str | None = None
    url: str | None = None


class GentleExitCopyFile(ContentModel):
    title: str
    condolence: str
    resources_intro: str
    resources: list[GentleExitResource]
    clear_data_confirmation: str


class FunnelCopyFile(Notes):
    version: int
    common: dict[str, str]
    landing: Landing
    quiz_intro: QuizIntro
    quiz: QuizCopy
    loader: Loader
    plan_preview: PlanPreview
    paywall: Paywall
    today: TodayCopyFile
    gentle_exit: GentleExitCopyFile
    errors: dict[str, str]


# ---------------------------------------------------------------- lessons/*.json


class PatternStep(ContentModel):
    id: str
    label: str
    example: str


class Pattern(ContentModel):
    name: str
    steps: list[PatternStep]


class OptionLabel(ContentModel):
    id: str
    label: str


class ScreenBase(ContentModel):
    """Fields every lesson screen may carry: `part` (label above the screen, served) and `sec`
    (seconds, content-only: validated against the lesson `minutes`, never served)."""

    part: str | None = None
    sec: int | None = None


class PositionalModel(ContentModel):
    """A model the package files write as a positional array, e.g. `[text, correct, feedback]`."""

    positions: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="before")
    @classmethod
    def _from_array(cls, data: Any) -> Any:
        if isinstance(data, list | tuple):
            if len(data) != len(cls.positions):
                raise ValueError(f"expected {len(cls.positions)} values {list(cls.positions)}")
            return dict(zip(cls.positions, data, strict=True))
        return data


def _with_ids(items: Any, prefix: str) -> Any:
    """Index-based ids (`o1..`, `a1..`): stable because content edits never reshuffle."""
    if not isinstance(items, list):
        return items
    out: list[Any] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, dict):
            item = {"id": f"{prefix}{index}", **item}
        out.append(item)
    return out


class IntroScreen(ScreenBase):
    id: str
    type: Literal["intro"]
    minutes: int
    title: str
    body: str
    bullets: list[str]
    image: str | None = None


class SetupOption(PositionalModel):
    positions = ("id", "label")
    id: str
    label: str


class SetupScreen(ScreenBase):
    id: str
    type: Literal["setup"]
    title: str
    body: str
    options: list[SetupOption]


class ScenarioVariant(ContentModel):
    intro: str | None = None
    setup: str
    line: str


class ScenarioAnswer(ContentModel):
    id: str
    text: str
    verdict: str
    feedback: str
    save_phrase: bool | None = None


class ScenarioOption(PositionalModel):
    positions = ("text", "verdict", "feedback")
    id: str = ""
    text: str
    verdict: str
    feedback: str
    save_phrase: bool | None = None


class ScenarioScreen(ScreenBase):
    """Canonical scenario: `*_by_variant` blocks plus the maps that resolve them.

    The old shape (`byVariant`, `answers` dict, `answersVariantMap`) is adapted by the validator
    below. The legacy fields stay filled for old-shape lessons until P9 replaces the renderer, so
    the API output is unchanged in the meantime; the new shape leaves them unset.
    """

    id: str
    type: Literal["scenario"]
    title: str | None = None
    note: str | None = None
    setup_by_variant: dict[str, str]
    line_by_variant: dict[str, str]
    options_by_variant: dict[str, list[ScenarioOption]]
    setup_variant_map: dict[str, str] = {}
    options_variant_map: dict[str, str] = {}
    # Transitional (old shape only).
    by_variant: dict[str, ScenarioVariant] | None = None
    question: str | None = None
    answers: dict[str, list[ScenarioAnswer]] | None = None
    answers_variant_map: dict[str, str] | None = None
    verdict_labels: dict[str, str] | None = None
    after_choice: str | None = None
    save_button: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _adapt(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if "byVariant" in data and "answers" in data:
            variants = data["byVariant"]
            data.setdefault("setupByVariant", {k: v["setup"] for k, v in variants.items()})
            data.setdefault("lineByVariant", {k: v["line"] for k, v in variants.items()})
            data.setdefault("optionsByVariant", data["answers"])
            maps = data.get("answersVariantMap", {})
            data.setdefault("setupVariantMap", maps)
            data.setdefault("optionsVariantMap", maps)
        by_variant = data.get("optionsByVariant")
        if isinstance(by_variant, dict):
            data["optionsByVariant"] = {
                k: _with_ids(_dicts(v, ScenarioOption), "a") for k, v in by_variant.items()
            }
        return data


class LessonQuizOption(PositionalModel):
    positions = ("text", "correct", "feedback")
    id: str = ""
    text: str
    correct: bool
    feedback: str


class QuizScreen(ScreenBase):
    id: str
    type: Literal["quiz"]
    title: str
    options: list[LessonQuizOption]

    @model_validator(mode="before")
    @classmethod
    def _ids(cls, data: Any) -> Any:
        if isinstance(data, dict) and "options" in data:
            data = {**data, "options": _with_ids(_dicts(data["options"], LessonQuizOption), "o")}
        return data


class Item(PositionalModel):
    positions = ("title", "text")
    title: str
    text: str


class Step(PositionalModel):
    positions = ("n", "title", "text")
    n: str
    title: str
    text: str


class Example(PositionalModel):
    positions = ("text", "why")
    text: str
    why: str


class StickyNote(PositionalModel):
    positions = ("line1", "line2")
    line1: str
    line2: str


class DoDont(ContentModel):
    do: list[str]
    dont: list[str]


class ContentScreen(ScreenBase):
    """Teaching screen with optional blocks, rendered in a fixed order (see PLAN-04 1.1)."""

    id: str
    type: Literal["content"]
    title: str
    body: list[str] | None = None
    body_by_variant: dict[str, list[str]] | None = None
    body_variant_map: dict[str, str] | None = None
    items: list[Item] | None = None
    steps: list[Step] | None = None
    dodont: DoDont | None = None
    examples: list[Example] | None = None
    example: StickyNote | None = None
    key_idea: str | None = None
    tip: str | None = None
    image: str | None = None


class BuilderOption(PositionalModel):
    positions = ("text", "correct")
    id: str = ""
    text: str
    correct: bool


class BuilderGroup(ContentModel):
    id: str = ""
    label: str
    options: list[BuilderOption]


class BuilderScreen(ScreenBase):
    id: str
    type: Literal["builder"]
    title: str
    body: str
    groups: list[BuilderGroup]

    @model_validator(mode="before")
    @classmethod
    def _groups(cls, data: Any) -> Any:
        if not isinstance(data, dict) or not isinstance(data.get("groups"), list):
            return data
        groups: list[Any] = []
        for index, group in enumerate(data["groups"], start=1):
            if isinstance(group, list | tuple) and len(group) == 2:
                group = {"label": group[0], "options": group[1]}
            if isinstance(group, dict):
                options = _with_ids(_dicts(group.get("options"), BuilderOption), "o")
                group = {"id": f"g{index}", **group, "options": options}
            groups.append(group)
        return {**data, "groups": groups}


class ResetOption(ContentModel):
    id: str
    label: str
    plan_text: str | None = None


class ResetScreen(ScreenBase):
    """Options are plain strings, or `[label, planText]` pairs (planText: the plan wording)."""

    id: str
    type: Literal["reset"]
    title: str
    body: str
    question: str
    options: list[ResetOption]
    image: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _options(cls, data: Any) -> Any:
        if not isinstance(data, dict) or not isinstance(data.get("options"), list):
            return data
        options: list[Any] = []
        for index, option in enumerate(data["options"], start=1):
            if isinstance(option, str):
                option = {"label": option}
            elif isinstance(option, list | tuple) and len(option) == 2:
                option = {"label": option[0], "plan_text": option[1]}
            if isinstance(option, dict):
                option = {"id": f"r{index}", **option}
            options.append(option)
        return {**data, "options": options}


def _dicts(items: Any, model: type[PositionalModel]) -> Any:
    """Arrays of a positional model become dicts so `_with_ids` can add the id."""
    if not isinstance(items, list):
        return items
    return [
        dict(zip(model.positions, item, strict=False)) if isinstance(item, list | tuple) else item
        for item in items
    ]


class MiniTaskOption(ContentModel):
    id: str
    label: str
    response: str | None = None
    correct: bool | None = None


class MiniTask(ContentModel):
    question: str
    options: list[MiniTaskOption]
    store_as: str | None = None
    all_correct: bool | None = None


class LearnScreen(ScreenBase):
    id: str
    type: Literal["learn"]
    title: str
    body: str | None = None
    bullets: dict[str, list[str]] | None = None
    bullets_variant_map: dict[str, str] | None = None
    extra_for_both: str | None = None
    extra_for_facility: str | None = None
    pattern_tip: str | None = None
    show_pattern: bool | None = None
    mini_task: MiniTask | None = None


class PhrasesReviewScreen(ScreenBase):
    """Review screen: the server fills it with the phrases the learner saved."""

    id: str
    type: Literal["phrases_review"]
    title: str
    intro: str
    empty_text: str


class Round(ContentModel):
    stage: str
    line: str
    mood: str


class RoleplaySummary(ContentModel):
    title: str
    first_vs_last: str
    best_phrase_label: str
    save_button: str
    again_button: str


class RoleplayLabels(ContentModel):
    partner: str
    not_saved: str
    thinking: str
    ai_down: str


class RoleplayScreen(ScreenBase):
    id: str
    type: Literal["roleplay"]
    prompt_file: str
    title: str
    intro: str
    goals: list[str]
    rounds_by_variant: dict[str, list[Round]]
    rounds_variant_map: dict[str, str]
    summary: RoleplaySummary
    labels: RoleplayLabels
    fallback_scenarios: list[str]


class IfThen(ContentModel):
    cue_by_variant: dict[str, str]
    cue_variant_map: dict[str, str]
    response_label: str
    response_default: str
    response_editable: bool
    reset_label: str
    reset_from: str


class DoNowItem(ContentModel):
    text: str
    action: str
    button: str


class DoNow(ContentModel):
    title: str
    by_variant: dict[str, DoNowItem]


class NoteTemplate(ContentModel):
    title: str
    example: str


class PlanScreen(ScreenBase):
    id: str
    type: Literal["plan"]
    title: str
    if_then: IfThen
    do_now: DoNow
    remind_button: str
    done_button: str
    note_template: NoteTemplate


class ConfidenceCheck(ContentModel):
    only_first_lesson: bool
    title: str
    scale: str
    items: list[OptionLabel]


class WrapScreen(ScreenBase):
    id: str
    type: Literal["wrap"]
    skill_line: str
    phrase_line: str
    pattern_line: str
    confidence_check: ConfidenceCheck | None = None
    tomorrow_line: str
    next_line: str
    title: str | None = None
    learned: list[str] | None = None
    # Shown instead of a next lesson when this is the last lesson built so far.
    all_done_line: str | None = None


LessonScreen = Annotated[
    IntroScreen
    | SetupScreen
    | ScenarioScreen
    | ContentScreen
    | QuizScreen
    | BuilderScreen
    | ResetScreen
    | LearnScreen
    | PhrasesReviewScreen
    | RoleplayScreen
    | PlanScreen
    | WrapScreen,
    Field(discriminator="type"),
]


class FallbackAnswer(ContentModel):
    text: str
    verdict: str
    feedback: str


class FallbackScenario(ContentModel):
    id: str
    setup: str
    line: str
    answers: list[FallbackAnswer]


class CheckInOption(ContentModel):
    id: str
    label: str
    response: str | None = None
    next: str | None = None


class CheckInFollowUp(ContentModel):
    if_answer: str
    question: str
    show_plan: bool
    options: list[CheckInOption]


class CheckIn(ContentModel):
    question: str
    options: list[CheckInOption]
    follow_up: CheckInFollowUp | None = None


class CheckInSet(ContentModel):
    by_variant: dict[str, CheckIn]
    check_in_variant_map: dict[str, str]


class TitledText(ContentModel):
    title: str
    text: str


class DoctorNote(ContentModel):
    text: str
    button: str


class PracticeRound(ContentModel):
    title: str
    prompt_file: str
    goals: list[str]
    rounds_by_variant: dict[str, list[Round]]
    rounds_variant_map: dict[str, str]


class Day2(ContentModel):
    check_in: CheckInSet
    follow_ups_didnt_help: list[TitledText]
    doctor_note: DoctorNote
    practice_round: PracticeRound
    next_lesson_prompt: str


class Recap(ContentModel):
    text: str
    if_check_in_helped: str


class LessonFile(Notes):
    id: str
    version: int
    module_id: str
    title: str
    minutes: int
    skill: str
    skill_label: str
    pattern: Pattern
    screens: list[LessonScreen]
    fallback_scenarios: list[FallbackScenario]
    day2: Day2
    recap_for_next_lesson: Recap

    def variant_ids(self) -> list[str]:
        """Variant ids from the setup screen (`setup`); empty for
        lessons without variants."""
        for screen in self.screens:
            if isinstance(screen, SetupScreen):
                return [option.id for option in screen.options]
        return []


# ---------------------------------------------------------------- app-copy.json


class AppCopyNav(ContentModel):
    today: str
    plan: str
    profile_page: str
    skills: str
    settings: str


class AppCopyPlan(ContentModel):
    title: str
    subtitle: str
    quick_guides_title: str
    quick_guides_caption: str


class AppCopyProfile(ContentModel):
    title: str
    privacy_note: str
    works_title: str
    about_title: str
    enjoys_title: str
    calms_title: str
    avoid_title: str
    rhythm_title: str
    contacts_title: str
    empty_phrases: str
    edit_note: str


class AppCopyCareCard(ContentModel):
    title: str
    purpose: str
    sharing_sentence: str


class AppCopyVisitSheet(ContentModel):
    title: str
    subtitle: str


class AppCopySkills(ContentModel):
    title: str
    subtitle: str


class AppCopySettings(ContentModel):
    title: str
    gentle_exit_entry: str
    gentle_exit_hint: str


class AppCopyWelcome(ContentModel):
    title: str
    body: str
    name_label: str


class AppCopyQuiz(ContentModel):
    right: str
    wrong: str


class AppCopyBuilder(ContentModel):
    all_correct: str
    not_yet: str


class AppCopyDoSkip(ContentModel):
    do_label: str
    skip_label: str


class AppCopyLesson(ContentModel):
    """Labels of the lesson player that the lesson files do not carry (no placeholders)."""

    verdict_labels: dict[str, str]
    after_choice: str
    save_button: str
    quiz: AppCopyQuiz
    builder: AppCopyBuilder
    do_skip: AppCopyDoSkip


class AppCopyFile(Notes):
    version: int
    nav: AppCopyNav
    plan: AppCopyPlan
    profile: AppCopyProfile
    care_card: AppCopyCareCard
    visit_sheet: AppCopyVisitSheet
    skills: AppCopySkills
    settings: AppCopySettings
    welcome: AppCopyWelcome
    lesson: AppCopyLesson


# ---------------------------------------------------------------- quick-guides.json

# Placeholders a guide may use (singular labels, as in the lessons).
GUIDE_PLACEHOLDERS = frozenset(
    {"recipient", "Recipient", "possessive", "Possessive", "pronoun", "Pronoun", "object"}
)
_GUIDE_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")


class GuideCommonModel(ContentModel):
    footer: str
    call_now_title: str
    steps_title: str
    then_title: str
    dont_title: str
    resources_title: str


class GuideResourceModel(ContentModel):
    label: str
    number: str
    tel: str


class GuideStepModel(ContentModel):
    title: str
    text: str


class GuideSourceModel(ContentModel):
    name: str
    url: str


class QuickGuideModel(ContentModel):
    id: str
    title: str
    summary: str
    urgency: Literal["emergency", "urgent", "planning", "support"]
    call_now: list[str]
    steps: list[GuideStepModel] = Field(min_length=1)
    then: list[str]
    dont: list[str]
    resources: list[str]
    sources: list[GuideSourceModel]

    def texts(self) -> list[str]:
        return [
            self.title,
            self.summary,
            *self.call_now,
            *(t for s in self.steps for t in (s.title, s.text)),
            *self.then,
            *self.dont,
        ]


class QuickGuidesFile(Notes):
    version: int
    common: GuideCommonModel
    resources: dict[str, GuideResourceModel]
    guides: list[QuickGuideModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_guides(self) -> "QuickGuidesFile":
        ids = [g.id for g in self.guides]
        if len(set(ids)) != len(ids):
            raise ValueError("guide ids must be unique")
        for guide in self.guides:
            for rid in guide.resources:
                if rid not in self.resources:
                    raise ValueError(f"guide '{guide.id}' uses unknown resource '{rid}'")
            for text in guide.texts():
                for name in _GUIDE_PLACEHOLDER.findall(text):
                    if name not in GUIDE_PLACEHOLDERS:
                        raise ValueError(f"guide '{guide.id}' uses placeholder {{{name}}}")
        return self
