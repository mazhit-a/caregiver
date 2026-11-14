"""Funnel routes: complete the quiz, preview the plan, the free gift sheet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.plan.use_cases import CompleteQuiz, GetGiftSheet, GetPlan, GetPlanPreview
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.presentation.api.deps import CurrentSession, SubscribedSession, get_clock, get_uow
from app.presentation.api.schemas.plan import (
    BeforeAfterOut,
    CompleteResponse,
    GiftPhraseOut,
    GiftResponse,
    PaceOut,
    PlanLessonOut,
    PlanLessonStatusOut,
    PlanModuleOut,
    PlanModuleStatusOut,
    PlanPreviewResponse,
    PlanResponse,
    QuickGuideOut,
    ReadinessOut,
)

router = APIRouter(tags=["plan"])


def _complete_quiz(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> CompleteQuiz:
    content: ContentProvider = request.app.state.content
    return CompleteQuiz(uow, content, clock)


def _get_plan_preview(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> GetPlanPreview:
    return GetPlanPreview(uow)


def _get_gift_sheet(request: Request, uow: Annotated[UnitOfWork, Depends(get_uow)]) -> GetGiftSheet:
    content: ContentProvider = request.app.state.content
    return GetGiftSheet(uow, content)


def _get_plan(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GetPlan:
    content: ContentProvider = request.app.state.content
    return GetPlan(uow, content, clock)


@router.post("/quiz/complete", response_model=CompleteResponse)
async def complete_quiz(
    session: CurrentSession, use_case: Annotated[CompleteQuiz, Depends(_complete_quiz)]
) -> CompleteResponse:
    result = await use_case.execute(session)
    return CompleteResponse(
        completed=True,
        completed_at=result.completed_at,
        rules_version=result.rules_version,
        content_version=result.content_version,
    )


@router.get("/plan/preview", response_model=PlanPreviewResponse)
async def plan_preview(
    session: CurrentSession, use_case: Annotated[GetPlanPreview, Depends(_get_plan_preview)]
) -> PlanPreviewResponse:
    view = await use_case.execute(session)
    plan = view.plan
    return PlanPreviewResponse(
        plan_intro=plan.plan_intro,
        what_we_heard=list(plan.what_we_heard),
        before_after=BeforeAfterOut(before=plan.before_after.before, after=plan.before_after.after),
        modules=[
            PlanModuleOut(
                id=m.id,
                title=m.title,
                reason=m.reason,
                status=m.status,
                in_first_30_days=m.in_first_30_days,
                lessons=[
                    PlanLessonOut(id=x.id, title=x.title, minutes=x.minutes, built=x.built)
                    for x in m.lessons
                ],
            )
            for m in plan.modules
        ],
        first_30_days=list(plan.first_30_days),
        first_lesson_id=plan.first_lesson_id,
        quick_guides=[
            QuickGuideOut(id=g.id, title=g.title, highlight=g.highlight) for g in plan.quick_guides
        ],
        loader_lines=list(plan.loader_lines),
        pace=PaceOut(
            lessons_per_week=plan.pace.lessons_per_week,
            minutes_per_lesson=plan.pace.minutes_per_lesson,
            label=plan.pace.label,
        ),
        readiness=ReadinessOut(
            modules_total=plan.readiness.modules_total, lessons_total=plan.readiness.lessons_total
        ),
        rules_version=view.rules_version,
        content_version=view.content_version,
        built_at=view.built_at,
    )


@router.get("/plan/gift", response_model=GiftResponse)
async def plan_gift(
    session: CurrentSession, use_case: Annotated[GetGiftSheet, Depends(_get_gift_sheet)]
) -> GiftResponse:
    sheet = await use_case.execute(session)
    return GiftResponse(
        title=sheet.title,
        intro=sheet.intro,
        phrases=[GiftPhraseOut(id=p.id, text=p.text, when=p.when) for p in sheet.phrases],
        footer=sheet.footer,
    )


@router.get("/plan", response_model=PlanResponse)
async def get_plan(
    session: SubscribedSession, use_case: Annotated[GetPlan, Depends(_get_plan)]
) -> PlanResponse:
    view = await use_case.execute(session)
    return PlanResponse(
        modules=[
            PlanModuleStatusOut(
                id=m.id,
                title=m.title,
                reason=m.reason,
                lessons=[
                    PlanLessonStatusOut(
                        id=x.id,
                        title=x.title,
                        minutes=x.minutes,
                        status=x.status,
                        unlock_on=x.unlock_on,
                    )
                    for x in m.lessons
                ],
            )
            for m in view.modules
        ],
        hero_lesson_id=view.hero_lesson_id,
        lessons_per_week=view.lessons_per_week,
    )
