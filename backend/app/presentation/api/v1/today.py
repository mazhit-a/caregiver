"""Today route (behind the access gate): `past_due` and other blocked states never reach it."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.application.today.dto import CheckinChoice, TodayView
from app.application.today.use_cases import GetToday
from app.presentation.api.deps import AppInfoDep, SubscribedSession, get_clock, get_uow
from app.presentation.api.schemas.checkins import PlanQuoteOut
from app.presentation.api.schemas.today import (
    CareCardNudgeOut,
    CheckinCardOut,
    CheckinChoiceOut,
    CheckinFollowUpOut,
    DemoBlockOut,
    DemoControlOut,
    NextLessonOut,
    NextStepOut,
    PracticeRoundOut,
    ReadinessOut,
    SubscriptionNoticeOut,
    TodayResponse,
    VisitSheetLinkOut,
    WeeklyRhythmOut,
    WelcomeBackOut,
)

router = APIRouter(tags=["today"])

# The sections in the order Today shows them (TASK.md 6.10).
SECTION_ORDER = (
    "checkIn",
    "practiceRound",
    "careCardNudge",
    "nextStep",
    "weeklyRhythm",
    "readiness",
    "subscriptionNotice",
    "welcomeBack",
    "demo",
)


def _get_today(
    request: Request,
    info: AppInfoDep,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GetToday:
    content: ContentProvider = request.app.state.content
    return GetToday(uow, content, clock, info.demo_controls)


def _choices(options: list[CheckinChoice]) -> list[CheckinChoiceOut]:
    return [CheckinChoiceOut(id=o.id, label=o.label) for o in options]


def to_response(view: TodayView) -> TodayResponse:
    check_in = view.check_in
    present = {
        "checkIn": check_in is not None,
        "practiceRound": view.practice_round is not None,
        "careCardNudge": view.care_card_nudge is not None,
        "nextStep": True,
        "weeklyRhythm": True,
        "readiness": True,
        "subscriptionNotice": view.subscription_notice is not None,
        "welcomeBack": view.welcome_back is not None,
        "demo": view.demo is not None,
    }
    return TodayResponse(
        title=view.title,
        order=[name for name in SECTION_ORDER if present[name]],
        check_in=None
        if check_in is None
        else CheckinCardOut(
            plan_id=check_in.plan_id,
            question=check_in.question,
            options=_choices(check_in.options),
            follow_up=None
            if check_in.follow_up is None
            else CheckinFollowUpOut(
                if_answer=check_in.follow_up.if_answer,
                question=check_in.follow_up.question,
                options=_choices(check_in.follow_up.options),
            ),
            plan=PlanQuoteOut(
                cue=check_in.plan.cue, response=check_in.plan.response, reset=check_in.plan.reset
            ),
        ),
        practice_round=None
        if view.practice_round is None
        else PracticeRoundOut(
            lesson_id=view.practice_round.lesson_id,
            title=view.practice_round.title,
            rounds_total=view.practice_round.rounds_total,
            variant=view.practice_round.variant,
        ),
        care_card_nudge=None
        if view.care_card_nudge is None
        else CareCardNudgeOut(
            new_phrase_count=view.care_card_nudge.new_phrase_count, text=view.care_card_nudge.text
        ),
        next_step=NextStepOut(
            kind=view.next_step.kind,
            message=view.next_step.message,
            lesson=None
            if view.next_step.lesson is None
            else NextLessonOut(**vars(view.next_step.lesson)),
            unlock_text=view.next_step.unlock_text,
        ),
        weekly_rhythm=WeeklyRhythmOut(**vars(view.weekly_rhythm)),
        readiness=ReadinessOut(**vars(view.readiness)),
        subscription_notice=None
        if view.subscription_notice is None
        else SubscriptionNoticeOut(**vars(view.subscription_notice)),
        welcome_back=None
        if view.welcome_back is None
        else WelcomeBackOut(title=view.welcome_back.title, body=view.welcome_back.body),
        visit_sheet_link=VisitSheetLinkOut(label=view.visit_sheet_link),
        demo=None
        if view.demo is None
        else DemoBlockOut(
            label=view.demo.label,
            app_now=view.demo.app_now,
            app_today=view.demo.app_today,
            clock_offset_seconds=view.demo.clock_offset_seconds,
            controls=[DemoControlOut(id=c.id, label=c.label) for c in view.demo.controls],
        ),
    )


@router.get("/today", response_model=TodayResponse)
async def get_today(
    session: SubscribedSession, use_case: Annotated[GetToday, Depends(_get_today)]
) -> TodayResponse:
    return to_response(await use_case.execute(session))
