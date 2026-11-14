"""Pricing and billing routes. None of these are behind the access gate."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.billing.cancel import CancelSubscription, GetCancelPreview
from app.application.billing.checkout import CreateCheckout, ReconcileCheckout
from app.application.billing.use_cases import (
    GetPricing,
    GetSubscription,
    StartDemoSubscription,
    StartSubscription,
)
from app.application.ports import Clock, ContentProvider, PaymentGateway, UnitOfWork
from app.domain.billing.entities import Subscription
from app.presentation.api.deps import (
    CurrentSession,
    get_clock,
    get_optional_payment_gateway,
    get_payment_gateway,
    get_uow,
)
from app.presentation.api.schemas.billing import (
    CancelPreviewResponse,
    CancelResponse,
    CheckoutRequestBody,
    CheckoutResponse,
    CheckoutStatusResponse,
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


def _create_checkout(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    gateway: Annotated[PaymentGateway, Depends(get_payment_gateway)],
) -> CreateCheckout:
    content: ContentProvider = request.app.state.content
    return CreateCheckout(uow, content, clock, gateway, request.app.state.settings.public_app_url)


def _reconcile_checkout(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    gateway: Annotated[PaymentGateway, Depends(get_payment_gateway)],
) -> ReconcileCheckout:
    content: ContentProvider = request.app.state.content
    return ReconcileCheckout(uow, content, clock, gateway, StartSubscription(uow, content, clock))


def _cancel_preview(
    request: Request, uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> GetCancelPreview:
    content: ContentProvider = request.app.state.content
    return GetCancelPreview(uow, content)


def _cancel(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    gateway: Annotated[PaymentGateway | None, Depends(get_optional_payment_gateway)],
) -> CancelSubscription:
    return CancelSubscription(uow, clock, gateway)


def _to_response(subscription: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        status=subscription.status,
        plan_id=subscription.plan_id,
        source=subscription.source,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        renewal_count=subscription.renewal_count,
        auto_renew_consent_at=subscription.auto_renew_consent_at,
        billing_sync=subscription.billing_sync if subscription.source == "stripe" else "none",
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


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequestBody,
    session: CurrentSession,
    use_case: Annotated[CreateCheckout, Depends(_create_checkout)],
) -> CheckoutResponse:
    ref = await use_case.execute(session, body.auto_renew_consent, body.plan_id)
    return CheckoutResponse(checkout_id=ref.id, url=ref.url)


@router.get("/billing/checkout/{checkout_id}", response_model=CheckoutStatusResponse)
async def reconcile_checkout(
    checkout_id: str,
    session: CurrentSession,
    use_case: Annotated[ReconcileCheckout, Depends(_reconcile_checkout)],
) -> CheckoutStatusResponse:
    result = await use_case.execute(session, checkout_id)
    return CheckoutStatusResponse(
        paid=result.paid,
        message=None if result.paid else "No payment has been received for this checkout.",
        subscription=_to_response(result.subscription),
    )


@router.get("/billing/cancel-preview", response_model=CancelPreviewResponse)
async def cancel_preview(
    session: CurrentSession, use_case: Annotated[GetCancelPreview, Depends(_cancel_preview)]
) -> CancelPreviewResponse:
    view = await use_case.execute(session)
    return CancelPreviewResponse(
        plan_name=view.plan_name,
        saved_phrase_count=view.saved_phrase_count,
        care_card_published=view.care_card_published,
        end_date=view.end_date,
        status=view.status,
    )


@router.post("/billing/cancel", response_model=CancelResponse)
async def cancel(
    session: CurrentSession, use_case: Annotated[CancelSubscription, Depends(_cancel)]
) -> CancelResponse:
    result = await use_case.execute(session)
    return CancelResponse(status=result.status, end_date=result.end_date)
