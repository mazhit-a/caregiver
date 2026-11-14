"""Pricing catalogue (pricing.json as the domain reads it) and the disclosure values."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.billing.errors import UnknownPlan


@dataclass(frozen=True)
class PricingPlan:
    """One plan. There is deliberately no price-per-day anywhere."""

    id: str
    label: str
    intro_price: Decimal
    intro_days: int
    intro_period_text: str
    renew_price: Decimal
    renew_days: int
    renew_period_text: str
    stripe_intro_price_id: str
    stripe_renew_price_id: str
    stripe_intro_coupon_id: str

    def first_renewal_date(self, app_today: date) -> date:
        """The date the first renewal is charged: today plus the intro period."""
        return app_today + timedelta(days=self.intro_days)


@dataclass(frozen=True)
class Pricing:
    currency: str
    default_plan_id: str
    plans: tuple[PricingPlan, ...]

    def plan(self, plan_id: str | None) -> PricingPlan:
        """The plan with this id, or the default plan when `plan_id` is None."""
        wanted = plan_id or self.default_plan_id
        for plan in self.plans:
            if plan.id == wanted:
                return plan
        raise UnknownPlan(f"Unknown plan '{wanted}'", {"planId": wanted})
