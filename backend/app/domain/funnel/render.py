"""Renders the funnel strings: recipient labels, money and dates are filled here, once.

Pure: the app date is an argument. Money comes from `pricing.json` values only; there is no price
per day. The `**bold**` markers of the disclosure become segments, so no asterisk reaches a client.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.billing.pricing import Pricing, PricingPlan
from app.domain.funnel.copy import FunnelCopy
from app.domain.shared.labels import RecipientLabels, render_text

_BOLD = "**"


@dataclass(frozen=True)
class TextSegment:
    text: str
    strong: bool


@dataclass(frozen=True)
class PaywallPlanCopy:
    id: str
    label: str
    price_today: str
    detail: str
    disclosure: tuple[TextSegment, ...]
    consent_label: str
    pay_button_label: str
    first_renewal_date: str


@dataclass(frozen=True)
class FunnelCopyView:
    loader_title: str
    plan_preview_title: str
    plan_preview_cta: str
    highlight_label: str
    health_note: str
    paywall_headline: str
    paywall_subhead: str
    paywall_includes: tuple[str, ...]
    paywall_consent_required_error: str
    paywall_success: str
    paywall_returned_canceled: str
    default_plan_id: str
    plans: tuple[PaywallPlanCopy, ...]


def format_short_date(day: date) -> str:
    """ "Nov 15" (month abbreviation and day, no year)."""
    return f"{day:%b} {day.day}"


def format_money(amount: Decimal, money_format: str) -> str:
    return money_format.replace("{amount}", f"{amount:.2f}")


def split_bold(text: str) -> tuple[TextSegment, ...]:
    """Splits `a **b** c` into segments; the markers are dropped and the text is not trimmed."""
    parts = text.split(_BOLD)
    return tuple(
        TextSegment(part, strong=index % 2 == 1) for index, part in enumerate(parts) if part
    )


def _render_plan(
    plan: PricingPlan, copy: FunnelCopy, labels: RecipientLabels, app_today: date
) -> PaywallPlanCopy:
    price_today = format_money(plan.intro_price, copy.money_format)
    values = {
        "todayPrice": price_today,
        "introPeriod": plan.intro_period_text,
        "renewPrice": format_money(plan.renew_price, copy.money_format),
        "renewPeriod": plan.renew_period_text,
        "renewDate": format_short_date(plan.first_renewal_date(app_today)),
    }
    return PaywallPlanCopy(
        id=plan.id,
        label=plan.label,
        price_today=price_today,
        detail=render_text(copy.plan_detail, labels, values),
        disclosure=split_bold(render_text(copy.disclosure, labels, values)),
        consent_label=render_text(copy.consent_checkbox, labels, values),
        pay_button_label=render_text(copy.pay_button, labels, values),
        first_renewal_date=values["renewDate"],
    )


def render_funnel_copy(
    copy: FunnelCopy,
    pricing: Pricing,
    labels: RecipientLabels,
    what_we_heard: tuple[str, ...],
    app_today: date,
) -> FunnelCopyView:
    def fill(text: str) -> str:
        return render_text(text, labels)

    return FunnelCopyView(
        loader_title=fill(copy.loader_title),
        plan_preview_title=fill(copy.plan_preview_title),
        plan_preview_cta=fill(copy.plan_preview_cta),
        highlight_label=copy.highlight_label,
        health_note=copy.health_note,
        paywall_headline=fill(copy.paywall_headline),
        paywall_subhead=what_we_heard[0] if what_we_heard else "",
        paywall_includes=tuple(fill(t) for t in copy.paywall_includes),
        paywall_consent_required_error=copy.consent_required_error,
        paywall_success=fill(copy.success),
        paywall_returned_canceled=copy.returned_canceled,
        default_plan_id=pricing.default_plan_id,
        plans=tuple(_render_plan(p, copy, labels, app_today) for p in pricing.plans),
    )
