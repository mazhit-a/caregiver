"""One-off, idempotent Stripe TEST-mode setup for the prices in content/pricing.json.

Usage (from `backend/`): `uv run python -m scripts.stripe_setup`

Finds or creates, by the metadata key `pcn_key`, one product, per plan a renewal price, an intro
price and a one-time intro coupon (renewal price minus intro price), then writes the returned ids
into content/pricing.json. A second run creates nothing new. Refuses any key that is not a Stripe
test key.
"""

import json
import sys
from collections.abc import Callable, Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

import stripe

from app.infrastructure.config import Settings

PRICING_PATH = Path(__file__).resolve().parents[2] / "content" / "pricing.json"
METADATA_KEY = "pcn_key"
PRODUCT_KEY = "parent_care_navigator"
PRODUCT_NAME = "Kelper"
_TEST_PREFIXES = ("sk_test_", "rk_test_")


class SetupError(Exception):
    """A setup precondition failed (bad key, bad pricing file)."""


def ensure_test_key(key: str) -> None:
    if not key.startswith(_TEST_PREFIXES):
        raise SetupError(
            "Refusing to run: STRIPE_SECRET_KEY must be a test key (sk_test_/rk_test_)."
        )


def _cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def _find(items: Iterable[Any], key: str) -> Any | None:
    for item in items:
        if (item.to_dict().get("metadata") or {}).get(METADATA_KEY) == key:
            return item
    return None


def _get_or_create(
    items: Iterable[Any], key: str, create: Callable[..., Any], params: dict[str, Any]
) -> Any:
    """The existing object whose metadata key matches, else a new one created from `params`."""
    found = _find(items, key)
    return (
        found if found is not None else create(params={**params, "metadata": {METADATA_KEY: key}})
    )


def run_setup(client: stripe.StripeClient, pricing_path: Path = PRICING_PATH) -> dict[str, str]:
    """Ensure product, prices and coupons exist; write the ids into pricing.json. Returns ids."""
    v1 = client.v1
    pricing = json.loads(pricing_path.read_text(encoding="utf-8"))
    currency = str(pricing["currency"]).lower()
    product = _get_or_create(
        v1.products.list(params={"limit": 100, "active": True}).auto_paging_iter(),
        PRODUCT_KEY,
        v1.products.create,
        {"name": PRODUCT_NAME},
    )
    if getattr(product, "name", None) != PRODUCT_NAME:
        product = v1.products.update(product.id, params={"name": PRODUCT_NAME})
    prices = list(
        v1.prices.list(
            params={"product": product.id, "limit": 100, "active": True}
        ).auto_paging_iter()
    )
    coupons = list(v1.coupons.list(params={"limit": 100}).auto_paging_iter())
    written: dict[str, str] = {}
    for plan in pricing["plans"]:
        plan_id = str(plan["id"])
        intro = Decimal(str(plan["introPrice"]))
        renew = Decimal(str(plan["renewPrice"]))
        if renew <= intro:
            raise SetupError(f"Plan {plan_id}: the renewal price must exceed the intro price.")
        for field, key, amount, days in (
            ("stripeRenewPriceId", f"{plan_id}_renew", renew, int(plan["renewDays"])),
            ("stripeIntroPriceId", f"{plan_id}_intro", intro, int(plan["introDays"])),
        ):
            price = _get_or_create(
                prices,
                key,
                v1.prices.create,
                {
                    "product": product.id,
                    "currency": currency,
                    "unit_amount": _cents(amount),
                    "recurring": {"interval": "day", "interval_count": days},
                },
            )
            plan[field] = str(price.id)
        coupon = _get_or_create(
            coupons,
            f"{plan_id}_intro_coupon",
            v1.coupons.create,
            {
                "amount_off": _cents(renew - intro),
                "currency": currency,
                "duration": "once",
                "name": f"Intro price {plan_id}",
            },
        )
        plan["stripeIntroCouponId"] = str(coupon.id)
        written[plan_id] = plan["stripeRenewPriceId"]
    pricing_path.write_text(json.dumps(pricing, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return written


def main() -> int:
    settings = Settings()
    key = settings.stripe_secret_key
    try:
        ensure_test_key(key)
        if not settings.stripe_enabled:
            raise SetupError("Set STRIPE_SECRET_KEY to your own Stripe test key (not the dummy).")
        run_setup(stripe.StripeClient(key))
    except SetupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Stripe test ids written to {PRICING_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
