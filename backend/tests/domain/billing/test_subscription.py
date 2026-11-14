from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.billing.entities import (
    ALL_STATUSES,
    TRANSITIONS,
    Subscription,
    SubscriptionStatus,
)
from app.domain.billing.errors import AccessDenied, ConsentRequired, InvalidTransition

SID = UUID(int=1)
T0 = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
END = T0 + timedelta(days=28)

# TASK.md 6.6, written out independently of the table in the code.
LEGAL_PAIRS: set[tuple[str, str]] = {
    ("none", "active"),
    ("none", "demo"),
    ("active", "past_due"),
    ("past_due", "active"),
    ("past_due", "canceled"),
    ("active", "canceled"),  # provider deleted the subscription (cancel_now)
    ("active", "canceling"),
    ("demo", "canceling"),
    ("canceling", "canceled"),
    *((s, "ended") for s in ALL_STATUSES if s != "ended"),
}


def sub(status: SubscriptionStatus, **kw: object) -> Subscription:
    return Subscription(
        SID,
        status=status,
        plan_id="four_week",
        source="demo" if status == "demo" else "stripe",
        current_period_start=T0,
        current_period_end=END,
        **kw,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("current", ALL_STATUSES)
@pytest.mark.parametrize("target", ALL_STATUSES)
def test_transition_table(current: SubscriptionStatus, target: SubscriptionStatus) -> None:
    subscription = sub(current)
    if (current, target) in LEGAL_PAIRS:
        subscription.transition(target, T0, "test")
        assert subscription.status == target
        assert subscription.pull_history()[0].to_status == target
    else:
        with pytest.raises(InvalidTransition):
            subscription.transition(target, T0, "test")
        assert subscription.status == current
        assert subscription.pull_history() == []
    assert Subscription.can_transition(current, target) == ((current, target) in LEGAL_PAIRS)


def test_transition_table_in_code_matches_spec() -> None:
    assert {(a, b) for a, targets in TRANSITIONS.items() for b in targets} == LEGAL_PAIRS


def test_named_methods_follow_the_table() -> None:
    s = sub("none", auto_renew_consent_at=T0)
    s.start_stripe(T0, "four_week", END, "cus_1", "sub_1")
    assert s.status == "active"
    s.mark_past_due(T0)
    assert s.status == "past_due"
    s.renew(T0, END + timedelta(days=28))
    assert s.status == "active"
    s.cancel_at_period_end(T0)
    s.end_period(T0)
    assert s.status == "canceled"
    s.end_now(T0)
    assert s.status == "ended"
    with pytest.raises(InvalidTransition):
        s.mark_past_due(T0)


@pytest.mark.parametrize("status", ["active", "past_due", "canceling"])
def test_cancel_now_moves_to_canceled_with_history(status: SubscriptionStatus) -> None:
    s = sub(status)
    s.cancel_now(T0, "stripe")
    [entry] = s.pull_history()
    assert (entry.from_status, entry.to_status) == (status, "canceled")
    assert (entry.event, entry.source) == ("subscription_deleted", "stripe")


@pytest.mark.parametrize("status", ["none", "demo", "canceled", "ended"])
def test_cancel_now_rejected_elsewhere(status: SubscriptionStatus) -> None:
    with pytest.raises(InvalidTransition):
        sub(status).cancel_now(T0)


def test_start_requires_consent_first() -> None:
    s = Subscription(SID)
    with pytest.raises(ConsentRequired):
        s.start_demo(T0, "four_week", 28)
    assert s.status == "none"
    s.record_consent(T0)
    s.start_demo(T0, "four_week", 28)
    assert s.status == "demo"
    assert s.current_period_end == T0 + timedelta(days=28)


def test_start_records_history_with_app_now_and_source() -> None:
    app_now = T0 + timedelta(days=3, hours=2)  # app time, not wall-clock
    s = Subscription(SID, auto_renew_consent_at=T0)
    s.start_demo(app_now, "four_week", 28)
    [entry] = s.pull_history()
    assert (entry.at, entry.from_status, entry.to_status) == (app_now, "none", "demo")
    assert (entry.source, entry.event) == ("demo", "started")
    assert s.pull_history() == []


def test_renew_rolls_period_for_demo_and_keeps_status() -> None:
    s = sub("demo")
    s.renew(END, END + timedelta(days=28), event="demo_renewed")
    assert s.status == "demo"
    assert s.renewal_count == 1
    assert (s.current_period_start, s.current_period_end) == (END, END + timedelta(days=28))
    [entry] = s.pull_history()
    assert (entry.event, entry.from_status, entry.to_status) == ("demo_renewed", "demo", "demo")


@pytest.mark.parametrize("status", ["none", "canceling", "canceled", "ended"])
def test_renew_is_illegal_elsewhere(status: SubscriptionStatus) -> None:
    with pytest.raises(InvalidTransition):
        sub(status).renew(T0, END)


@pytest.mark.parametrize(
    ("status", "has_plan", "offset", "reason"),
    [
        ("none", False, 0, "no_plan"),
        ("none", True, 0, "no_subscription"),
        ("active", True, 0, None),
        ("demo", True, 0, None),
        ("past_due", True, 0, "past_due"),
        ("canceling", True, -1, None),
        ("canceling", True, 1, "no_subscription"),
        ("canceled", True, 0, "no_subscription"),
        ("ended", True, 0, "ended"),
    ],
)
def test_can_access(
    status: SubscriptionStatus, has_plan: bool, offset: int, reason: str | None
) -> None:
    at = END + timedelta(hours=offset)
    denied = sub(status).can_access(at, has_plan)
    if reason is None:
        assert denied is None
    else:
        assert isinstance(denied, AccessDenied)
        assert denied.reason == reason
        assert denied.code == "payment_required"
        assert denied.details == {"reason": reason}
