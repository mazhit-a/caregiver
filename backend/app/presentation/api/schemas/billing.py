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
    first_renewal_date: date | None


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
    billing_sync: str  # none | pending | done (Stripe Test Clock sync; none for demo sessions)


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


class CancelPreviewResponse(CamelModel):
    """What the user would lose by canceling. Facts only: no discount or offer fields."""

    plan_name: str
    saved_phrase_count: int
    care_card_published: bool
    end_date: datetime | None
    status: str


class CancelResponse(CamelModel):
    status: str
    end_date: datetime | None
