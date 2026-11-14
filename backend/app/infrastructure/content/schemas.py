"""Pydantic models of the content files. Unknown fields fail validation on purpose."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
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
    disclosure: str
    consent_checkbox: str
    consent_required_error: str
    pay_button: str
    test_mode_hint: str
    demo_button: str
    demo_note: str
    footer: str
    states: PaywallStates


class SavePlan(ContentModel):
    title: str
    body: str
    email_label: str
    cta: str
    skip: str
    note: str


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
    loader: Loader
    plan_preview: PlanPreview
    paywall: Paywall
    save_plan: SavePlan
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


class SetupQuestionScreen(ContentModel):
    id: str
    type: Literal["setup_question"]
    speaker: str
    text: str
    question: str
    store_as: str
    options: list[OptionLabel]


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


class ScenarioScreen(ContentModel):
    id: str
    type: Literal["scenario"]
    by_variant: dict[str, ScenarioVariant]
    question: str
    answers: dict[str, list[ScenarioAnswer]]
    answers_variant_map: dict[str, str]
    verdict_labels: dict[str, str]
    after_choice: str
    save_button: str


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


class LearnScreen(ContentModel):
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


class PhrasesReviewScreen(ContentModel):
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


class RoleplayScreen(ContentModel):
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


class PlanScreen(ContentModel):
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


class WrapScreen(ContentModel):
    id: str
    type: Literal["wrap"]
    skill_line: str
    phrase_line: str
    pattern_line: str
    confidence_check: ConfidenceCheck | None = None
    tomorrow_line: str
    next_line: str
    # Shown instead of a next lesson when this is the last lesson built so far.
    all_done_line: str | None = None


LessonScreen = Annotated[
    SetupQuestionScreen
    | ScenarioScreen
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
        """Variant ids from the setup question; empty for lessons without variants."""
        for screen in self.screens:
            if isinstance(screen, SetupQuestionScreen):
                return [option.id for option in screen.options]
        return []
