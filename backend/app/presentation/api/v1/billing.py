"""Pricing and billing routes. None of these are behind the access gate."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.billing.use_cases import (
    GetPricing,
    GetSubscription,
    StartDemoSubscription,
    StartSubscription,
)
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.billing.entities import Subscription
from app.presentation.api.deps import CurrentSession, get_clock, get_uow
from app.presentation.api.schemas.billing import (
    DemoSubscribeRequest,
    PricingPlanOut,
    PricingResponse,
    SubscriptionResponse,
)

router = APIRouter(tags=["billing"])


def _get_pricing(request: Request, clock: Annotated[Clock, Depends(get_clock)]) -> GetPricing:
    content: ContentProvider = request.app.state.content
    return GetPricing(content, clock)


def _get_subscription(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> GetSubscription:
    return GetSubscription(uow)


def _start_demo(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> StartDemoSubscription:
    content: ContentProvider = request.app.state.content
    return StartDemoSubscription(uow, StartSubscription(uow, content, clock))


def _to_response(subscription: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        status=subscription.status,
        plan_id=subscription.plan_id,
        source=subscription.source,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        renewal_count=subscription.renewal_count,
        auto_renew_consent_at=subscription.auto_renew_consent_at,
    )


@router.get("/pricing", response_model=PricingResponse)
async def pricing(
    session: CurrentSession, use_case: Annotated[GetPricing, Depends(_get_pricing)]
) -> PricingResponse:
    view = use_case.execute(session)
    return PricingResponse(
        currency=view.currency,
        default_plan_id=view.default_plan_id,
        plans=[
            PricingPlanOut(
                id=p.id,
                label=p.label,
                price_today=float(p.price_today),
                renewal_price=float(p.renewal_price),
                intro_period_text=p.intro_period_text,
                renew_period_text=p.renew_period_text,
                intro_days=p.intro_days,
                renew_days=p.renew_days,
                first_renewal_date=p.first_renewal_date,
            )
            for p in view.plans
        ],
    )


@router.post("/billing/demo", response_model=SubscriptionResponse)
async def subscribe_demo(
    body: DemoSubscribeRequest,
    session: CurrentSession,
    use_case: Annotated[StartDemoSubscription, Depends(_start_demo)],
) -> SubscriptionResponse:
    return _to_response(await use_case.execute(session, body.auto_renew_consent, body.plan_id))


@router.get("/billing/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    session: CurrentSession, use_case: Annotated[GetSubscription, Depends(_get_subscription)]
) -> SubscriptionResponse:
    return _to_response(await use_case.execute(session))
