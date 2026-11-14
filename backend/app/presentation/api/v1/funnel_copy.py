"""Funnel copy route: finished, recipient- and price-aware strings. Session only, not gated."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.funnel_copy.use_cases import GetFunnelCopy
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.presentation.api.deps import CurrentSession, get_clock, get_uow
from app.presentation.api.schemas.funnel_copy import (
    FunnelCopyResponse,
    LoaderCopyOut,
    PaywallCopyOut,
    PaywallPlanOut,
    PaywallStatesOut,
    PlanPreviewCopyOut,
    QuizCopyOut,
    TextSegmentOut,
)

router = APIRouter(tags=["funnel-copy"])


def _get_funnel_copy(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GetFunnelCopy:
    content: ContentProvider = request.app.state.content
    return GetFunnelCopy(uow, content, clock)


@router.get("/funnel-copy", response_model=FunnelCopyResponse)
async def funnel_copy(
    session: CurrentSession, use_case: Annotated[GetFunnelCopy, Depends(_get_funnel_copy)]
) -> FunnelCopyResponse:
    view = await use_case.execute(session)
    return FunnelCopyResponse(
        quiz=QuizCopyOut(health_note=view.health_note),
        loader=LoaderCopyOut(title=view.loader_title),
        plan_preview=PlanPreviewCopyOut(
            title=view.plan_preview_title,
            cta=view.plan_preview_cta,
            highlight_label=view.highlight_label,
        ),
        paywall=PaywallCopyOut(
            headline=view.paywall_headline,
            subhead=view.paywall_subhead,
            includes=list(view.paywall_includes),
            consent_required_error=view.paywall_consent_required_error,
            states=PaywallStatesOut(
                success=view.paywall_success, returned_canceled=view.paywall_returned_canceled
            ),
            default_plan_id=view.default_plan_id,
            plans=[
                PaywallPlanOut(
                    id=p.id,
                    label=p.label,
                    price_today=p.price_today,
                    detail=p.detail,
                    disclosure=[TextSegmentOut(text=s.text, strong=s.strong) for s in p.disclosure],
                    consent_label=p.consent_label,
                    pay_button_label=p.pay_button_label,
                    first_renewal_date=p.first_renewal_date,
                )
                for p in view.plans
            ],
        ),
    )
