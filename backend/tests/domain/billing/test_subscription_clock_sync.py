from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.billing.entities import Subscription

T0 = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


def _stripe_sub() -> Subscription:
    return Subscription(
        uuid4(), "active", source="stripe", stripe_test_clock_id="clock_1", stripe_clock_at=T0
    )


def test_clock_advances_only_forward() -> None:
    sub = _stripe_sub()
    assert sub.clock_needs_advance(T0 + timedelta(days=1))
    assert not sub.clock_needs_advance(T0)
    assert not sub.clock_needs_advance(T0 - timedelta(days=1))


def test_demo_subscription_or_missing_clock_never_needs_advance() -> None:
    demo = Subscription(uuid4(), "demo", source="demo")
    assert not demo.clock_needs_advance(T0 + timedelta(days=1))
    no_clock = Subscription(uuid4(), "active", source="stripe")
    assert not no_clock.clock_needs_advance(T0 + timedelta(days=1))


def test_billing_sync_goes_pending_then_done_and_ready_without_pending_is_ignored() -> None:
    sub = _stripe_sub()
    assert sub.billing_sync == "none" and not sub.clock_ready()
    sub.clock_advanced(T0 + timedelta(days=1))
    assert sub.billing_sync == "pending" and sub.stripe_clock_at == T0 + timedelta(days=1)
    assert sub.clock_ready() and sub.billing_sync == "done"
    assert not sub.clock_ready()
