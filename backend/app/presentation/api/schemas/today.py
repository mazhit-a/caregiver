"""Today response: wording, ids, dates and counts only (no role-play text, no profile data)."""

from datetime import date, datetime
from typing import Literal

from app.presentation.api.schemas.base import CamelModel
from app.presentation.api.schemas.checkins import PlanQuoteOut


class CheckinChoiceOut(CamelModel):
    id: str
    label: str


class CheckinFollowUpOut(CamelModel):
    if_answer: str
    question: str
    options: list[CheckinChoiceOut]


class CheckinCardOut(CamelModel):
    plan_id: str
    question: str
    options: list[CheckinChoiceOut]
    follow_up: CheckinFollowUpOut | None
    plan: PlanQuoteOut


class PracticeRoundOut(CamelModel):
    lesson_id: str
    title: str
    rounds_total: int
    variant: str | None
    context: Literal["practice_round"] = "practice_round"


class CareCardNudgeOut(CamelModel):
    new_phrase_count: int
    text: str


class NextLessonOut(CamelModel):
    lesson_id: str
    title: str
    module_id: str
    reason: str
    status: Literal["locked", "available", "in_progress", "done", "coming_later"]
    unlock_on: date | None
    minutes: int
    skill_label: str | None


class NextStepOut(CamelModel):
    kind: Literal["lesson", "rest", "all_done"]
    message: str | None
    lesson: NextLessonOut | None
    unlock_text: str | None


class WeeklyRhythmOut(CamelModel):
    done: int
    target: int
    text: str


class ReadinessOut(CamelModel):
    done: int
    total: int
    text: str


class SubscriptionNoticeOut(CamelModel):
    kind: Literal["renews_on", "renewed", "ends_on"]
    on: date
    text: str


class WelcomeBackOut(CamelModel):
    title: str
    body: str


class DemoControlOut(CamelModel):
    id: str
    label: str


class DemoBlockOut(CamelModel):
    label: str
    app_now: datetime
    app_today: date
    clock_offset_seconds: int
    controls: list[DemoControlOut]


class VisitSheetLinkOut(CamelModel):
    """A pointer only: the visit sheet itself lives at `path`."""

    label: str
    path: str = "/api/visit-sheet"


class TodayResponse(CamelModel):
    """Fields appear in the order Today shows them; `order` lists the sections present."""

    title: str
    order: list[str]
    check_in: CheckinCardOut | None
    practice_round: PracticeRoundOut | None
    care_card_nudge: CareCardNudgeOut | None
    next_step: NextStepOut
    weekly_rhythm: WeeklyRhythmOut
    readiness: ReadinessOut
    subscription_notice: SubscriptionNoticeOut | None
    welcome_back: WelcomeBackOut | None
    visit_sheet_link: VisitSheetLinkOut
    demo: DemoBlockOut | None
