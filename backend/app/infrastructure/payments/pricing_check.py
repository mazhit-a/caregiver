"""Startup check: with Stripe enabled, pricing.json must hold real Stripe test ids."""

from app.domain.billing.pricing import Pricing

PLACEHOLDER_MARKER = "REPLACE"


class StripePricingNotConfigured(RuntimeError):
    """Stripe is enabled but pricing.json still has placeholder ids."""


def ensure_stripe_ids_resolved(pricing: Pricing) -> None:
    """Raise with a clear message when any Stripe price or coupon id is still a placeholder."""
    unresolved = [
        f"{plan.id}.{field}"
        for plan in pricing.plans
        for field, value in (
            ("stripeIntroPriceId", plan.stripe_intro_price_id),
            ("stripeRenewPriceId", plan.stripe_renew_price_id),
            ("stripeIntroCouponId", plan.stripe_intro_coupon_id),
        )
        if PLACEHOLDER_MARKER in value
    ]
    if unresolved:
        raise StripePricingNotConfigured(
            "Stripe is enabled but content/pricing.json still has placeholder ids ("
            + ", ".join(unresolved)
            + "). Run `uv run python -m scripts.stripe_setup` with your Stripe TEST key, "
            "or unset STRIPE_SECRET_KEY to use demo mode only."
        )
