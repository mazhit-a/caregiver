"""stripe_setup against a faked Stripe client (in-memory, no network)."""

import json
import shutil
from itertools import count
from pathlib import Path
from typing import Any, cast

import pytest
import stripe

from scripts.stripe_setup import SetupError, ensure_test_key, run_setup

REAL_PRICING = Path(__file__).resolve().parents[3] / "content" / "pricing.json"


class _Collection:
    def __init__(self, prefix: str) -> None:
        self.objects: list[stripe.StripeObject] = []
        self.created = 0
        self.updated = 0
        self._ids = count(1)
        self._prefix = prefix
        self.params_seen: list[dict[str, Any]] = []

    def list(self, params: dict[str, Any] | None = None) -> Any:
        page = type("Page", (), {})()
        page.auto_paging_iter = lambda: iter(list(self.objects))
        return page

    def create(self, params: dict[str, Any]) -> stripe.StripeObject:
        self.created += 1
        self.params_seen.append(params)
        obj = stripe.StripeObject.construct_from(
            {"id": f"{self._prefix}_{next(self._ids)}", **params}, "sk_test_fake"
        )
        self.objects.append(obj)
        return obj

    def update(self, id: str, params: dict[str, Any]) -> stripe.StripeObject:
        obj = next(o for o in self.objects if o["id"] == id)
        obj["name"] = params["name"]
        self.updated += 1
        return obj


class FakeStripeClient:
    def __init__(self) -> None:
        self.v1 = type("V1", (), {})()
        self.v1.products = _Collection("prod")
        self.v1.prices = _Collection("price")
        self.v1.coupons = _Collection("coupon")

    def created_total(self) -> int:
        return sum(c.created for c in (self.v1.products, self.v1.prices, self.v1.coupons))


def _client(fake: FakeStripeClient) -> stripe.StripeClient:
    return cast(stripe.StripeClient, fake)


@pytest.fixture
def pricing_file(tmp_path: Path) -> Path:
    path = tmp_path / "pricing.json"
    shutil.copy(REAL_PRICING, path)
    return path


def test_stripe_setup_creates_products_prices_coupons_and_writes_ids_with_faked_stripe_client(
    pricing_file: Path,
) -> None:
    fake = FakeStripeClient()
    run_setup(_client(fake), pricing_file)
    assert len(fake.v1.products.objects) == 1
    assert len(fake.v1.prices.objects) == 4  # renew + intro for two plans
    assert len(fake.v1.coupons.objects) == 2
    by_key = {p["metadata"]["pcn_key"]: p for p in fake.v1.prices.params_seen}
    renew = by_key["four_week_renew"]
    assert (renew["unit_amount"], renew["currency"]) == (2999, "usd")
    assert renew["recurring"] == {"interval": "day", "interval_count": 28}
    assert by_key["twelve_week_intro"]["unit_amount"] == 4999
    coupon = fake.v1.coupons.params_seen[0]
    assert coupon["amount_off"] == 1500 and coupon["duration"] == "once"  # 29.99 - 14.99

    data = json.loads(pricing_file.read_text())
    four = data["plans"][0]
    assert not any("REPLACE" in json.dumps(plan) for plan in data["plans"])
    ids = {
        four["stripeRenewPriceId"],
        four["stripeIntroPriceId"],
        data["plans"][1]["stripeRenewPriceId"],
        data["plans"][1]["stripeIntroPriceId"],
    }
    assert ids == {o.id for o in fake.v1.prices.objects}
    assert four["stripeIntroCouponId"] == fake.v1.coupons.objects[0].id
    assert data["plans"][0]["introPrice"] == 14.99  # the rest of the file is untouched


def test_stripe_setup_second_run_creates_nothing_new(pricing_file: Path) -> None:
    fake = FakeStripeClient()
    run_setup(_client(fake), pricing_file)
    first_file = pricing_file.read_text()
    created = fake.created_total()
    run_setup(_client(fake), pricing_file)
    assert fake.created_total() == created
    assert pricing_file.read_text() == first_file


def test_stripe_setup_reuses_existing_objects_found_by_metadata_key(pricing_file: Path) -> None:
    fake = FakeStripeClient()
    fake.v1.products.create(params={"name": "x", "metadata": {"pcn_key": "parent_care_navigator"}})
    fake.v1.products.created = 0
    run_setup(_client(fake), pricing_file)
    assert fake.v1.products.created == 0 and len(fake.v1.products.objects) == 1


def test_stripe_setup_renames_an_existing_product_with_an_old_name(pricing_file: Path) -> None:
    fake = FakeStripeClient()
    fake.v1.products.create(params={"name": "x", "metadata": {"pcn_key": "parent_care_navigator"}})
    run_setup(_client(fake), pricing_file)
    assert fake.v1.products.updated == 1
    assert fake.v1.products.objects[0]["name"] == "Kelper"
    run_setup(_client(fake), pricing_file)
    assert fake.v1.products.updated == 1


@pytest.mark.parametrize("key", ["sk_live_abc", "rk_live_abc", "", "pk_test_abc"])
def test_stripe_setup_refuses_live_key(key: str) -> None:
    with pytest.raises(SetupError, match="test key"):
        ensure_test_key(key)


def test_stripe_setup_accepts_test_keys() -> None:
    ensure_test_key("sk_test_abc")
    ensure_test_key("rk_test_abc")
