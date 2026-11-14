from datetime import UTC, datetime, timedelta

from app.application.billing.events import BillingEvent
from app.application.billing.stripe_events import HandleStripeEvent
from app.domain.billing.entities import Subscription
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.billing import test_start_subscription as start_tests
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork

content = start_tests.content
_with_plan = start_tests._with_plan
END = datetime(2026, 3, 2, tzinfo=UTC)


async def _consented(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider, **kw: object
) -> Session:
    """A session with a plan and the auto-renew consent stored, as `CreateCheckout` leaves it."""
    session = await _with_plan(uow, clock, content, **kw)  # type: ignore[arg-type]
    await uow.subscriptions.save(
        Subscription(session.id, auto_renew_consent_at=clock.now(), stripe_customer_id="cus_1")
    )
    return session


def _paid(event_id: str, session_id: object) -> BillingEvent:
    return BillingEvent(
        event_id,
        "checkout.session.completed",
        session_id=session_id,  # type: ignore[arg-type]
        customer_id="cus_1",
        subscription_id="sub_1",
        plan_id="four_week",
        paid=True,
    )


async def test_event_recorded_but_not_finished_is_handled_again(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _consented(uow, clock, content)
    await uow.stripe_events.begin("evt_1", "checkout.session.completed", clock.now())  # crashed
    handled = await HandleStripeEvent(uow, content, clock).execute(_paid("evt_1", session.id))
    assert handled is True
    sub = await uow.subscriptions.get(session.id)
    assert sub is not None and sub.status == "active"
    assert uow.stripe_events.events["evt_1"][2] is not None  # now marked processed
    again = await HandleStripeEvent(uow, content, clock).execute(_paid("evt_1", session.id))
    assert again is False


async def test_status_changes_use_app_now_and_source_stripe(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _consented(uow, clock, content, offset=timedelta(days=5))
    handler = HandleStripeEvent(uow, content, clock)
    await handler.execute(_paid("evt_1", session.id))
    await handler.execute(BillingEvent("evt_2", "invoice.payment_failed", customer_id="cus_1"))
    history = await uow.subscription_history.list_for_session(session.id)
    assert [(e.to_status, e.source) for e in history] == [
        ("active", "stripe"),
        ("past_due", "stripe"),
    ]
    assert all(e.at == clock.now() + timedelta(days=5) for e in history)


async def test_events_the_status_does_not_allow_are_skipped_without_error(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _consented(uow, clock, content)
    handler = HandleStripeEvent(uow, content, clock)
    await handler.execute(_paid("evt_1", session.id))
    await handler.execute(
        BillingEvent("evt_2", "customer.subscription.deleted", customer_id="cus_1")
    )
    for n, event_type in enumerate(
        ["invoice.paid", "invoice.payment_failed", "customer.subscription.deleted"]
    ):
        await handler.execute(
            BillingEvent(f"evt_late_{n}", event_type, customer_id="cus_1", period_end=END)
        )
    sub = await uow.subscriptions.get(session.id)
    assert sub is not None and sub.status == "canceled" and sub.renewal_count == 0
    assert len(await uow.subscription_history.list_for_session(session.id)) == 2


async def test_registry_has_the_six_planned_event_types(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    assert set(HandleStripeEvent(uow, content, clock).registry) == {
        "checkout.session.completed",
        "invoice.paid",
        "invoice.payment_failed",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "test_helpers.test_clock.ready",
    }
