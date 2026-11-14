"""Pricing and subscription response schemas."""

from datetime import date, datetime

from app.presentation.api.schemas.base import CamelModel


class PricingPlanOut(CamelModel):
    id: str
    label: str
    price_today: float
    renewal_price: float
    intro_period_text: str
    renew_period_text: str
    intro_days: int
    renew_days: int
    first_renewal_date: date


class PricingResponse(CamelModel):
    currency: str
    default_plan_id: str
    plans: list[PricingPlanOut]


class DemoSubscribeRequest(CamelModel):
    auto_renew_consent: bool
    plan_id: str | None = None


class SubscriptionResponse(CamelModel):
    status: str
    plan_id: str | None
    source: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    renewal_count: int
    auto_renew_consent_at: datetime | None


class CheckoutRequestBody(CamelModel):
    auto_renew_consent: bool
    plan_id: str | None = None


class CheckoutResponse(CamelModel):
    checkout_id: str
    url: str


class CheckoutStatusResponse(CamelModel):
    paid: bool
    message: str | None
    subscription: SubscriptionResponse
