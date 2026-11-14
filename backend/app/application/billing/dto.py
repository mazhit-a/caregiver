"""Billing DTOs."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.billing.entities import SubscriptionSource


@dataclass(frozen=True)
class PricingPlanView:
    id: str
    label: str
    price_today: Decimal
    renewal_price: Decimal
    intro_period_text: str
    renew_period_text: str
    intro_days: int
    renew_days: int
    first_renewal_date: date  # app_today + introDays


@dataclass(frozen=True)
class PricingView:
    currency: str
    default_plan_id: str
    plans: list[PricingPlanView]


@dataclass(frozen=True)
class StartRequest:
    """Input of `StartSubscription`, the single entry for every subscription start.

    `auto_renew_consent` must be True unless the consent was stored earlier (the Stripe checkout
    stores it when the Checkout Session is created). `plan_id=None` means the default plan.
    Stripe starts also pass `period_end` and the Stripe ids; demo starts leave them None.
    """

    source: SubscriptionSource
    auto_renew_consent: bool
    plan_id: str | None = None
    period_end: datetime | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
