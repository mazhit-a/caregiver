"""`GET /api/today`: the return-visit screen, composed in the order of TASK.md 6.10.

Read-only. Every sentence comes from content (`funnel-copy.json` `today`, the lesson files, the
plan); the clock is the injected `Clock` (app time = real now + session offset).
"""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.application.checkins.use_cases import checkin_block, plan_quote
from app.application.plan.dto import PlanLessonView, PlanView
from app.application.plan.use_cases import GetPlan
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.application.roleplay.lesson_source import render, rounds_for
from app.application.today.dto import (
    CareCardNudge,
    CheckinCard,
    CheckinChoice,
    CheckinFollowUp,
    DemoBlock,
    DemoControlView,
    NextLessonCard,
    NextStep,
    NoticeCard,
    PracticeRoundCard,
    ReadinessRing,
    TodayView,
    WeeklyRhythm,
    WelcomeBack,
)
from app.domain.billing.entities import Subscription
from app.domain.care_card.entities import CareCard
from app.domain.care_card.policies import new_phrase_count
from app.domain.lessons.plans import IfThenPlan
from app.domain.phrases.entities import SavedPhrase
from app.domain.plan.entities import StoredPlan
from app.domain.plan.errors import NoPlan
from app.domain.roleplay.run import RunContext, RunRecord
from app.domain.schedule.entities import LessonState
from app.domain.schedule.next_lesson import NextLesson, select_next_lesson
from app.domain.session.entities import Session
from app.domain.shared.labels import RecipientLabels, render_text
from app.domain.today.checkins import checkin_due
from app.domain.today.copy import TodayCopy
from app.domain.today.notice import subscription_notice
from app.domain.today.rhythm import is_welcome_back, sessions_this_week


def format_date(day: date) -> str:
    """ "November 21" (no year: every date on Today is within the coming weeks)."""
    return f"{day:%B} {day.day}"


@dataclass(frozen=True)
class _Facts:
    """Everything Today reads, loaded in one transaction."""

    stored: StoredPlan
    plan_view: PlanView
    latest_plan: IfThenPlan | None
    answered: bool
    variant: str | None
    card: CareCard | None
    saved: list[SavedPhrase]
    runs: list[RunRecord]
    subscription: Subscription


class GetToday:
    def __init__(
        self, uow: UnitOfWork, content: ContentProvider, clock: Clock, demo_controls: bool
    ) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._demo_controls = demo_controls
        self._get_plan = GetPlan(uow, content, clock)

    async def execute(self, session: Session) -> TodayView:
        facts = await self._load(session)
        real_now = self._clock.now()
        now = session.app_now(real_now)
        today = session.app_today(real_now)
        copy = self._content.today_copy()
        labels = self._content.lesson_recipient_labels(
            session.recipient_key or "", session.display_name
        )
        plan = facts.latest_plan
        plan_day = None if plan is None else plan.created_at.astimezone(_zone(session)).date()
        return TodayView(
            title=render_text(copy.title, labels),
            check_in=self._check_in(session, facts, now) if plan_day is not None else None,
            practice_round=(
                self._practice_round(session, facts)
                if plan_day is not None and plan_day < today
                else None
            ),
            care_card_nudge=_nudge(copy, labels, new_phrase_count(facts.card, facts.saved)),
            next_step=_next_step(copy, labels, facts, self._skill_labels()),
            weekly_rhythm=_rhythm(copy, labels, facts, today, session.timezone),
            readiness=_readiness(copy, labels, facts),
            subscription_notice=_notice(copy, labels, facts, now, session.timezone),
            welcome_back=_welcome_back(copy, session, now),
            visit_sheet_link=copy.visit_sheet_link,
            demo=self._demo(session, copy, now, today),
        )

    async def _load(self, session: Session) -> _Facts:
        plan_view = await self._get_plan.execute(session)  # raises NoPlan, extends the schedule
        async with self._uow:
            stored = await self._uow.plans.get(session.id)
            latest = await self._uow.if_then_plans.latest(session.id)
            checkin = await self._uow.checkins.get(session.id, latest.lesson_id) if latest else None
            progress = (
                await self._uow.lesson_progress.get(session.id, latest.lesson_id)
                if latest
                else None
            )
            card = await self._uow.care_cards.get_current(session.id)
            saved = await self._uow.saved_phrases.list_for_session(session.id)
            runs = await self._uow.roleplay_runs.list_finished(session.id)
            subscription = await self._uow.subscriptions.get(session.id)
        if stored is None:
            raise NoPlan()
        return _Facts(
            stored,
            plan_view,
            latest,
            checkin is not None,
            progress.variant if progress else None,
            card,
            list(saved),
            runs,
            subscription or Subscription(session.id),
        )

    def _skill_labels(self) -> dict[str, str]:
        rules = self._content.plan_rules()
        return {
            lesson.id: rules.skills[m.skill]
            for m in rules.modules
            if m.skill in rules.skills
            for lesson in m.lessons
        }

    def _check_in(self, session: Session, facts: _Facts, now: datetime) -> CheckinCard | None:
        """The question while the check-in is due (the plan is from an earlier app day and has no
        answer); the plan is quoted in the user's own words."""
        plan = facts.latest_plan
        if plan is None or facts.answered:
            return None
        if not checkin_due(plan.created_at, now, session.timezone, has_checkin=False):
            return None
        _, block = checkin_block(self._content, session, plan.lesson_id, facts.variant)
        follow = block.get("followUp")
        return CheckinCard(
            plan.lesson_id,
            block["question"],
            [CheckinChoice(o["id"], o["label"]) for o in block["options"]],
            None
            if follow is None
            else CheckinFollowUp(
                follow["ifAnswer"],
                follow["question"],
                [CheckinChoice(o["id"], o["label"]) for o in follow["options"]],
            ),
            plan_quote(plan),
        )

    def _practice_round(self, session: Session, facts: _Facts) -> PracticeRoundCard | None:
        """The lesson's `day2.practiceRound` for the stored variant, offered with or without
        a check-in answer once the plan is a day old."""
        plan = facts.latest_plan
        if plan is None:
            return None
        lesson = render(self._content, session, plan.lesson_id, facts.variant)
        rounds = rounds_for(lesson, RunContext.PRACTICE_ROUND, facts.variant)
        return PracticeRoundCard(
            plan.lesson_id, lesson["day2"]["practiceRound"]["title"], len(rounds), facts.variant
        )

    def _demo(
        self, session: Session, copy: TodayCopy, now: datetime, today: date
    ) -> DemoBlock | None:
        if not self._demo_controls:
            return None
        return DemoBlock(
            copy.demo_label,
            now,
            today,
            int(session.clock_offset.total_seconds()),
            [DemoControlView(c.id, c.label) for c in copy.demo_controls],
        )


def _zone(session: Session) -> ZoneInfo:
    return ZoneInfo(session.timezone)


def _nudge(copy: TodayCopy, labels: RecipientLabels, count: int) -> CareCardNudge | None:
    if count <= 0:
        return None
    text = copy.care_card_nudge_one if count == 1 else copy.care_card_nudge_many
    return CareCardNudge(count, render_text(text, labels, {"count": str(count)}))


def _lesson_card(
    next_lesson: NextLesson, lessons: dict[str, PlanLessonView], skills: dict[str, str]
) -> NextLessonCard:
    minutes = lessons[next_lesson.lesson_id].minutes
    return NextLessonCard(
        next_lesson.lesson_id,
        next_lesson.title,
        next_lesson.module_id,
        next_lesson.reason,
        next_lesson.status,
        next_lesson.unlock_on,
        minutes,
        skills.get(next_lesson.lesson_id),
    )


def _next_step(
    copy: TodayCopy, labels: RecipientLabels, facts: _Facts, skills: dict[str, str]
) -> NextStep:
    lessons = {lesson.id: lesson for module in facts.plan_view.modules for lesson in module.lessons}
    states = [LessonState(item.id, item.status, item.unlock_on) for item in lessons.values()]
    chosen = select_next_lesson(facts.stored.plan.modules, states)
    if chosen is None:
        return NextStep("all_done", render_text(copy.all_built_done, labels), None, None)
    card = _lesson_card(chosen, lessons, skills)
    if chosen.status == "locked" and chosen.unlock_on is not None:
        unlock = render_text(copy.next_unlock, labels, {"date": format_date(chosen.unlock_on)})
        return NextStep("rest", render_text(copy.rest_message, labels), card, unlock)
    return NextStep("lesson", None, card, None)


def _rhythm(
    copy: TodayCopy, labels: RecipientLabels, facts: _Facts, today: date, timezone: str
) -> WeeklyRhythm:
    finished = (run.finished_at for run in facts.runs if run.finished_at is not None)
    done = sessions_this_week(finished, today, timezone)
    target = facts.stored.lessons_per_week
    text = render_text(copy.weekly_rhythm, labels, {"done": str(done), "target": str(target)})
    return WeeklyRhythm(done, target, text)


def _readiness(copy: TodayCopy, labels: RecipientLabels, facts: _Facts) -> ReadinessRing:
    """Lessons done / total in the first-30-days modules only."""
    first30 = {m.id for m in facts.stored.plan.modules if m.in_first_30_days}
    lessons = [
        lesson
        for module in facts.plan_view.modules
        if module.id in first30
        for lesson in module.lessons
    ]
    done = sum(1 for lesson in lessons if lesson.status == "done")
    text = render_text(copy.readiness, labels, {"done": str(done), "total": str(len(lessons))})
    return ReadinessRing(done, len(lessons), text)


def _notice(
    copy: TodayCopy, labels: RecipientLabels, facts: _Facts, now: datetime, timezone: str
) -> NoticeCard | None:
    notice = subscription_notice(facts.subscription, now, timezone, copy.renewed_notice_days)
    if notice is None:
        return None
    wording = {"renews_on": copy.renews_on, "renewed": copy.renewed, "ends_on": copy.ends_on}
    text = render_text(wording[notice.kind], labels, {"date": format_date(notice.on)})
    return NoticeCard(notice.kind, notice.on, text)


def _welcome_back(copy: TodayCopy, session: Session, now: datetime) -> WelcomeBack | None:
    if not is_welcome_back(session.previous_last_seen_at, now, copy.welcome_back_after_days):
        return None
    return WelcomeBack(copy.welcome_back_title, copy.welcome_back_body)
