"""Plain domain objects for the plan builder: rules (input) and the built plan (output)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

ModuleOrder = Literal["first", "noticing_second", "scored", "later"]
ModuleStatus = Literal["current", "next", "later"]


# ---------------------------------------------------------------- rules (input)


@dataclass(frozen=True)
class LessonRule:
    id: str
    title: str
    minutes: int
    built: bool


@dataclass(frozen=True)
class ModuleRule:
    id: str
    title: str
    order: ModuleOrder
    reason: str | None
    base_score: int | None
    lessons: tuple[LessonRule, ...]


@dataclass(frozen=True)
class BoostRule:
    module: str
    points: int
    reason: str
    all: tuple[str, ...] = ()
    any: tuple[str, ...] | None = None
    none: tuple[str, ...] | None = None


@dataclass(frozen=True)
class QuickGuideRule:
    id: str
    title: str
    highlight_if: tuple[str, ...]


@dataclass(frozen=True)
class PaceRules:
    lessons_per_week: Mapping[str, int]  # "pace:5" -> 3, plus the key "default"
    label: str  # "About {minutes} minutes a lesson, {perWeek} lessons a week"


@dataclass(frozen=True)
class HeardSentenceRule:
    slots: tuple[str, ...]
    prefix: str | None = None
    join: str | None = None
    list_join: str | None = None
    last_join: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class BeforeAfterRule:
    before: str
    after: str


@dataclass(frozen=True)
class LoaderLineRule:
    text: str
    always: bool = False
    any: tuple[str, ...] | None = None


@dataclass(frozen=True)
class PhraseRule:
    id: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class PlanRules:
    version: int
    first_module_id: str
    first_module_reason_by_branch: Mapping[str, str]
    first_lesson_id: str
    modules: tuple[ModuleRule, ...]
    boosts: tuple[BoostRule, ...]
    quick_guides: tuple[QuickGuideRule, ...]
    pace: PaceRules
    plan_intro: Mapping[str, str]  # "confidence:low" -> text, plus "default"
    heard_sentences: tuple[HeardSentenceRule, ...]
    before_after: Mapping[str, BeforeAfterRule]
    loader_lines: tuple[LoaderLineRule, ...]
    phrases: tuple[PhraseRule, ...]
    gift_phrase_count: int


@dataclass(frozen=True)
class HeardFragment:
    """One answer's contribution to "What we heard" (quiz option `heard`), in answer order."""

    slot: str
    text: str  # may hold {placeholders}


# ---------------------------------------------------------------- plan (output)


@dataclass(frozen=True)
class PlanLesson:
    id: str
    title: str
    minutes: int
    built: bool


@dataclass(frozen=True)
class PlanModule:
    id: str
    title: str
    reason: str
    status: ModuleStatus
    in_first_30_days: bool
    lessons: tuple[PlanLesson, ...]


@dataclass(frozen=True)
class PlanQuickGuide:
    id: str
    title: str
    highlight: bool  # shown first, marked "For now"


@dataclass(frozen=True)
class Pace:
    lessons_per_week: int
    minutes_per_lesson: int
    label: str


@dataclass(frozen=True)
class Readiness:
    """Totals for the "x of y lessons done" ring: Module 1 plus the next two modules."""

    modules_total: int
    lessons_total: int


@dataclass(frozen=True)
class BuiltPlan:
    rules_version: int
    plan_intro: str
    what_we_heard: tuple[str, ...]
    before_after: BeforeAfterRule
    modules: tuple[PlanModule, ...]
    first_30_days: tuple[str, ...]  # module ids
    first_lesson_id: str
    quick_guides: tuple[PlanQuickGuide, ...]
    loader_lines: tuple[str, ...]
    pace: Pace
    readiness: Readiness
    gift_phrase_ids: tuple[str, ...]
