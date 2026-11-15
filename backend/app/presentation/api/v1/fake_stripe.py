"""The in-app fake Stripe checkout. Mounted by `main.py` only when `FAKE_STRIPE=true`.

Not behind the access gate and not session-token authenticated: like Stripe's hosted checkout, the
unguessable checkout id is the capability. Card numbers are read from the body, evaluated, and
dropped: nothing stores or logs them.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from app.application.billing.fake_checkout import (
    CancelFakeCheckout,
    FakeCard,
    GetFakeCheckout,
    PayFakeCheckout,
)
from app.application.billing.stripe_events import HandleStripeEvent
from app.application.ports import Clock, ContentProvider, FakeCheckoutStore, UnitOfWork
from app.presentation.api.deps import get_clock, get_uow
from app.presentation.api.schemas.base import CamelModel

router = APIRouter(prefix="/fake-stripe", tags=["fake-stripe"])


class FakeCheckoutResponse(CamelModel):
    fake: Literal[True] = True
    checkout_id: str
    status: str  # open | paid | canceled
    plan_id: str
    plan_label: str
    currency: str
    amount_today: float
    intro_period_text: str
    renewal_price: float
    renew_period_text: str
    first_renewal_date: date
    display_label: str | None
    success_url: str
    cancel_url: str


class FakePayRequest(CamelModel):
    card_number: str = Field(min_length=1, max_length=32)
    exp_month: int = Field(ge=1, le=12)
    exp_year: int = Field(ge=0, le=9999)  # 2 or 4 digits
    cvc: str = Field(max_length=8)
    authenticated: bool = False  # confirm the 3-D Secure step (card 4000 0025 0000 3155)


class FakePayResponse(CamelModel):
    fake: Literal[True] = True
    status: Literal["paid", "requires_action"]
    success_url: str


class FakeCancelResponse(CamelModel):
    fake: Literal[True] = True
    status: Literal["canceled"] = "canceled"
    cancel_url: str


def _store(request: Request) -> FakeCheckoutStore:
    store: FakeCheckoutStore = request.app.state.fake_checkout_store
    return store


def _content(request: Request) -> ContentProvider:
    content: ContentProvider = request.app.state.content
    return content


def _get(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GetFakeCheckout:
    return GetFakeCheckout(uow, _content(request), clock, _store(request))


def _pay(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> PayFakeCheckout:
    content = _content(request)
    return PayFakeCheckout(
        uow, content, clock, _store(request), HandleStripeEvent(uow, content, clock)
    )


def _cancel(request: Request, uow: Annotated[UnitOfWork, Depends(get_uow)]) -> CancelFakeCheckout:
    return CancelFakeCheckout(uow, _store(request))


def _money(value: Decimal) -> float:
    return float(value)


@router.get("/checkout/{checkout_id}", response_model=FakeCheckoutResponse)
async def get_checkout(
    checkout_id: str, use_case: Annotated[GetFakeCheckout, Depends(_get)]
) -> FakeCheckoutResponse:
    view = await use_case.execute(checkout_id)
    return FakeCheckoutResponse(
        checkout_id=view.checkout_id,
        status=view.status,
        plan_id=view.plan_id,
        plan_label=view.plan_label,
        currency=view.currency,
        amount_today=_money(view.amount_today),
        intro_period_text=view.intro_period_text,
        renewal_price=_money(view.renewal_price),
        renew_period_text=view.renew_period_text,
        first_renewal_date=view.first_renewal_date,
        display_label=view.display_label,
        success_url=view.success_url,
        cancel_url=view.cancel_url,
    )


@router.post("/checkout/{checkout_id}/pay", response_model=FakePayResponse)
async def pay_checkout(
    checkout_id: str, body: FakePayRequest, use_case: Annotated[PayFakeCheckout, Depends(_pay)]
) -> FakePayResponse:
    result = await use_case.execute(
        checkout_id,
        FakeCard(body.card_number, body.exp_month, body.exp_year, body.cvc, body.authenticated),
    )
    return FakePayResponse(status=result.status, success_url=result.success_url)


@router.post("/checkout/{checkout_id}/cancel", response_model=FakeCancelResponse)
async def cancel_checkout(
    checkout_id: str, use_case: Annotated[CancelFakeCheckout, Depends(_cancel)]
) -> FakeCancelResponse:
    return FakeCancelResponse(cancel_url=await use_case.execute(checkout_id))
