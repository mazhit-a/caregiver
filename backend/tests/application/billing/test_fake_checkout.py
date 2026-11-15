from datetime import timedelta
from decimal import Decimal
from itertools import count

import pytest

from app.application.billing.checkout import CreateCheckout
from app.application.billing.events import BillingEvent
from app.application.billing.fake_checkout import (
    CancelFakeCheckout,
    FakeCard,
    GetFakeCheckout,
    PayFakeCheckout,
)
from app.application.billing.payments import CheckoutRequest
from app.application.billing.stripe_events import HandleStripeEvent
from app.domain.billing.errors import CardError, CheckoutNotFound, FakeCheckoutClosed
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.payments.fake_stripe import FakeStripeGateway
from tests.application.billing import test_start_subscription as start_tests
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork

content = start_tests.content
_with_plan = start_tests._with_plan
GOOD = FakeCard("4242 4242 4242 4242", 12, 2030, "123")


class _Tokens:
    def __init__(self) -> None:
        self._n = count(1)

    def new_token(self) -> str:
        return f"tok{next(self._n):012d}"


class _Env:
    def __init__(
        self, uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
    ) -> None:
        self.uow, self.clock, self.content = uow, clock, content
        self.events: list[BillingEvent] = []
        self.handle = HandleStripeEvent(uow, content, clock)
        self.gateway = FakeStripeGateway(
            _Tokens(),
            "https://app.example/",
            lambda plan_id: content.pricing().plan(plan_id).renew_days,
            self._sink,
        )

    async def _sink(self, event: BillingEvent) -> bool:
        self.events.append(event)
        return await self.handle.execute(event)

    async def checkout(self) -> tuple[Session, str]:
        session = await _with_plan(self.uow, self.clock, self.content)
        ref = await CreateCheckout(
            self.uow, self.content, self.clock, self.gateway, "https://app.example"
        ).execute(session, True, None)
        return session, ref.id

    def pay(self) -> PayFakeCheckout:
        return PayFakeCheckout(self.uow, self.content, self.clock, self.gateway, self.handle)

    async def status(self, session: Session) -> str:
        sub = await self.uow.subscriptions.get(session.id)
        return sub.status if sub else "none"


@pytest.fixture
def env(uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider) -> _Env:
    return _Env(uow, clock, content)


async def test_checkout_url_is_same_origin_fake_checkout_page(env: _Env) -> None:
    _, checkout_id = await env.checkout()
    record = env.gateway.get(checkout_id)
    assert record is not None
    ref = await env.gateway.create_checkout_session(
        CheckoutRequest(
            record.customer_id,
            record.session_id,
            record.plan_id,
            "price",
            "coupon",
            record.amount_today,
            record.success_url,
            record.cancel_url,
        )
    )
    assert checkout_id.startswith("cs_fake_")
    assert ref.url == f"https://app.example/fake-checkout/{ref.id}"


async def test_summary_shows_plan_amount_renewal_and_resolved_urls(env: _Env) -> None:
    _, checkout_id = await env.checkout()
    view = await GetFakeCheckout(env.uow, env.content, env.clock, env.gateway).execute(checkout_id)
    plan = env.content.pricing().plan(None)
    assert (view.plan_label, view.amount_today, view.renewal_price) == (
        plan.label,
        plan.intro_price,
        plan.renew_price,
    )
    assert view.first_renewal_date == env.clock.now().date() + timedelta(days=plan.intro_days)
    assert view.status == "open"
    assert view.success_url == f"https://app.example/checkout/return?checkout_id={checkout_id}"
    assert view.cancel_url == "https://app.example/paywall?checkout=canceled"
    assert isinstance(view.amount_today, Decimal)


async def test_unknown_checkout_is_not_found_everywhere(env: _Env) -> None:
    with pytest.raises(CheckoutNotFound):
        await GetFakeCheckout(env.uow, env.content, env.clock, env.gateway).execute("cs_fake_x")
    with pytest.raises(CheckoutNotFound):
        await env.pay().execute("cs_fake_x", GOOD)
    with pytest.raises(CheckoutNotFound):
        await CancelFakeCheckout(env.uow, env.gateway).execute("cs_fake_x")


async def test_paying_goes_through_the_checkout_completed_event_and_starts_stripe_subscription(
    env: _Env,
) -> None:
    session, checkout_id = await env.checkout()
    assert (await env.gateway.retrieve_checkout_session(checkout_id)).paid is False
    result = await env.pay().execute(checkout_id, GOOD)
    assert result.status == "paid"
    sub = await env.uow.subscriptions.get(session.id)
    assert sub is not None and sub.status == "active" and sub.source == "stripe"
    plan = env.content.pricing().plan(None)
    assert sub.current_period_end == env.clock.now() + timedelta(days=plan.intro_days)
    info = await env.gateway.retrieve_checkout_session(checkout_id)
    assert info.paid and info.session_id == session.id
    [event_type] = [v[0] for v in env.uow.stripe_events.events.values()]
    assert event_type == "checkout.session.completed"


async def test_paying_twice_is_idempotent(env: _Env) -> None:
    session, checkout_id = await env.checkout()
    await env.pay().execute(checkout_id, GOOD)
    again = await env.pay().execute(checkout_id, GOOD)
    assert again.status == "paid"
    history = await env.uow.subscription_history.list_for_session(session.id)
    assert len(history) == 1 and len(env.uow.stripe_events.events) == 1


@pytest.mark.parametrize(
    ("card", "code", "decline"),
    [
        (FakeCard("4000000000000002", 12, 2030, "123"), "card_declined", "generic_decline"),
        (FakeCard("4000000000009995", 12, 2030, "123"), "card_declined", "insufficient_funds"),
        (FakeCard("4000000000000069", 12, 2030, "123"), "expired_card", "expired_card"),
        (FakeCard("4000000000000127", 12, 2030, "123"), "incorrect_cvc", "incorrect_cvc"),
        (FakeCard("1111111111111111", 12, 2030, "123"), "card_declined", "generic_decline"),
        (FakeCard("4242424242424242", 1, 2020, "123"), "expired_card", "expired_card"),
    ],
)
async def test_refused_cards_raise_and_leave_everything_unchanged(
    env: _Env, card: FakeCard, code: str, decline: str
) -> None:
    session, checkout_id = await env.checkout()
    with pytest.raises(CardError) as caught:
        await env.pay().execute(checkout_id, card)
    assert caught.value.code == code
    assert caught.value.details == {"declineCode": decline, "fake": True}
    assert await env.status(session) == "none"
    assert env.uow.stripe_events.events == {}
    record = env.gateway.get(checkout_id)
    assert record is not None and record.status == "open" and record.last_outcome == "declined"
    assert (await env.pay().execute(checkout_id, GOOD)).status == "paid"  # may retry


async def test_only_last4_and_outcome_are_remembered(env: _Env) -> None:
    _, checkout_id = await env.checkout()
    await env.pay().execute(checkout_id, GOOD)
    record = env.gateway.get(checkout_id)
    assert record is not None and record.last4 == "4242" and record.last_outcome == "succeeds"
    assert "4242424242424242" not in repr(record)


async def test_three_d_secure_needs_the_authenticate_step(env: _Env) -> None:
    session, checkout_id = await env.checkout()
    card = FakeCard("4000 0025 0000 3155", 12, 2030, "123")
    first = await env.pay().execute(checkout_id, card)
    assert first.status == "requires_action" and await env.status(session) == "none"
    done = await env.pay().execute(
        checkout_id, FakeCard(card.number, 12, 2030, "123", authenticated=True)
    )
    assert done.status == "paid" and await env.status(session) == "active"


async def test_cancel_closes_the_checkout_and_it_stays_unpaid(env: _Env) -> None:
    session, checkout_id = await env.checkout()
    url = await CancelFakeCheckout(env.uow, env.gateway).execute(checkout_id)
    assert url == "https://app.example/paywall?checkout=canceled"
    assert (await env.gateway.retrieve_checkout_session(checkout_id)).paid is False
    with pytest.raises(FakeCheckoutClosed):
        await env.pay().execute(checkout_id, GOOD)
    assert await env.status(session) == "none"


async def test_cannot_cancel_a_paid_checkout(env: _Env) -> None:
    _, checkout_id = await env.checkout()
    await env.pay().execute(checkout_id, GOOD)
    with pytest.raises(FakeCheckoutClosed):
        await CancelFakeCheckout(env.uow, env.gateway).execute(checkout_id)


async def test_clock_advance_renews_through_invoice_paid_and_resolves_billing_sync(
    env: _Env,
) -> None:
    session, checkout_id = await env.checkout()
    await env.pay().execute(checkout_id, GOOD)
    sub = await env.uow.subscriptions.get(session.id)
    assert sub is not None and sub.stripe_test_clock_id and sub.current_period_end
    first_end = sub.current_period_end
    sub.clock_advanced(first_end + timedelta(hours=1))
    await env.uow.subscriptions.save(sub)
    await env.gateway.advance_test_clock(sub.stripe_test_clock_id, first_end + timedelta(hours=1))
    renewed = await env.uow.subscriptions.get(session.id)
    assert renewed is not None
    assert renewed.status == "active" and renewed.renewal_count == 1
    assert renewed.current_period_end == first_end + timedelta(
        days=env.content.pricing().plan(None).renew_days
    )
    assert renewed.billing_sync == "done"


async def test_card_0341_checkout_succeeds_then_first_renewal_goes_past_due(env: _Env) -> None:
    session, checkout_id = await env.checkout()
    await env.pay().execute(checkout_id, FakeCard("4000000000000341", 12, 2030, "123"))
    assert await env.status(session) == "active"
    sub = await env.uow.subscriptions.get(session.id)
    assert sub is not None and sub.stripe_test_clock_id and sub.current_period_end
    await env.gateway.advance_test_clock(
        sub.stripe_test_clock_id, sub.current_period_end + timedelta(hours=1)
    )
    assert await env.status(session) == "past_due"


async def test_cancel_at_period_end_then_clock_advance_ends_the_subscription(env: _Env) -> None:
    session, checkout_id = await env.checkout()
    await env.pay().execute(checkout_id, GOOD)
    sub = await env.uow.subscriptions.get(session.id)
    assert sub is not None and sub.stripe_subscription_id and sub.stripe_test_clock_id
    assert sub.current_period_end
    await env.gateway.cancel_at_period_end(sub.stripe_subscription_id)
    await env.gateway.advance_test_clock(
        sub.stripe_test_clock_id, sub.current_period_end + timedelta(hours=1)
    )
    assert await env.status(session) == "canceled"
