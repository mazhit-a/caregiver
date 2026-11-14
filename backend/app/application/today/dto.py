"""DTOs of the Today use case. Text fields are final wording (content, placeholders filled)."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from app.application.checkins.use_cases import PlanQuote
from app.domain.schedule.entities import LessonStatus
from app.domain.today.notice import NoticeKind

NextKind = Literal["lesson", "rest", "all_done"]


@dataclass(frozen=True)
class CheckinChoice:
    id: str
    label: str


@dataclass(frozen=True)
class CheckinFollowUp:
    if_answer: str
    question: str
    options: list[CheckinChoice]


@dataclass(frozen=True)
class CheckinCard:
    """The question of the lesson's `day2.checkIn` with the user's own plan quoted. The answers'
    response texts come back from `POST /api/checkins`."""

    plan_id: str
    question: str
    options: list[CheckinChoice]
    follow_up: CheckinFollowUp | None
    plan: PlanQuote


@dataclass(frozen=True)
class PracticeRoundCard:
    """Runs through the role-play endpoints with `context: "practice_round"`."""

    lesson_id: str
    title: str
    rounds_total: int
    variant: str | None


@dataclass(frozen=True)
class CareCardNudge:
    new_phrase_count: int
    text: str


@dataclass(frozen=True)
class NextLessonCard:
    lesson_id: str
    title: str
    module_id: str
    reason: str
    status: LessonStatus
    unlock_on: date | None
    minutes: int
    skill_label: str | None


@dataclass(frozen=True)
class NextStep:
    """`lesson`: an unlocked lesson is the hero. `rest`: the next lesson is not open yet (the
    rest message, `lesson` and `unlock_text` say when). `all_done`: every built lesson is done."""

    kind: NextKind
    message: str | None
    lesson: NextLessonCard | None
    unlock_text: str | None


@dataclass(frozen=True)
class WeeklyRhythm:
    done: int
    target: int
    text: str


@dataclass(frozen=True)
class ReadinessRing:
    done: int
    total: int
    text: str


@dataclass(frozen=True)
class NoticeCard:
    kind: NoticeKind
    on: date
    text: str


@dataclass(frozen=True)
class WelcomeBack:
    title: str
    body: str


@dataclass(frozen=True)
class DemoControlView:
    id: str
    label: str


@dataclass(frozen=True)
class DemoBlock:
    label: str
    app_now: datetime
    app_today: date
    clock_offset_seconds: int
    controls: list[DemoControlView]


@dataclass(frozen=True)
class TodayView:
    title: str
    check_in: CheckinCard | None
    practice_round: PracticeRoundCard | None
    care_card_nudge: CareCardNudge | None
    next_step: NextStep
    weekly_rhythm: WeeklyRhythm
    readiness: ReadinessRing
    subscription_notice: NoticeCard | None
    welcome_back: WelcomeBack | None
    visit_sheet_link: str
    demo: DemoBlock | None
