from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.billing.checkout import CreateCheckout, ReconcileCheckout
from app.application.billing.use_cases import StartSubscription
from app.domain.billing.errors import (
    AlreadySubscribed,
    CheckoutNotFound,
    ConsentRequired,
    PaymentGatewayError,
)
from app.domain.plan.errors import NoPlan
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.billing import test_start_subscription as start_tests
from tests.fakes.clock import FixedClock
from tests.fakes.payments import FakePaymentGateway
from tests.fakes.unit_of_work import FakeUnitOfWork

content = start_tests.content  # the shared module-scoped content fixture
_session = start_tests._session
_with_plan = start_tests._with_plan
BASE = "https://app.example"


def _checkout(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,
    gateway: FakePaymentGateway,
) -> CreateCheckout:
    return CreateCheckout(uow, content, clock, gateway, BASE + "/")


def _reconcile(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,
    gateway: FakePaymentGateway,
) -> ReconcileCheckout:
    return ReconcileCheckout(uow, content, clock, gateway, StartSubscription(uow, content, clock))


async def test_checkout_without_consent_raises_and_calls_nothing(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session = await _with_plan(uow, clock, content)
    with pytest.raises(ConsentRequired):
        await _checkout(uow, clock, content, gateway).execute(session, False, None)
    assert gateway.customers == [] and gateway.checkout_requests == []
    assert uow.subscriptions.saves == []


async def test_checkout_without_plan_raises_no_plan(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock, timedelta(0))
    with pytest.raises(NoPlan):
        await _checkout(uow, clock, content, FakePaymentGateway()).execute(session, True, None)


async def test_customer_created_with_test_clock_at_app_now(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session = await _with_plan(uow, clock, content, offset=timedelta(days=3))
    await _checkout(uow, clock, content, gateway).execute(session, True, None)
    assert gateway.customers == [(session.id, clock.now() + timedelta(days=3))]


async def test_checkout_request_to_stripe_has_only_session_uuid_plan_and_coupon(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session = await _with_plan(uow, clock, content)
    ref = await _checkout(uow, clock, content, gateway).execute(session, True, "twelve_week")
    [request] = gateway.checkout_requests
    plan = content.pricing().plan("twelve_week")
    assert request.session_id == session.id
    assert request.plan_id == "twelve_week"
    assert request.price_id == plan.stripe_renew_price_id  # renewal price, not the intro price
    assert request.coupon_id == plan.stripe_intro_coupon_id
    assert request.amount_today == Decimal("49.99")
    assert request.success_url == f"{BASE}/checkout/return?checkout_id={{CHECKOUT_SESSION_ID}}"
    assert request.cancel_url.startswith(BASE)
    assert ref.id.startswith("cs_test_fake")
    # The request type has no field that could carry a name, email or quiz value.
    assert {f for f in request.__dataclass_fields__} == {
        "customer_id",
        "session_id",
        "plan_id",
        "price_id",
        "coupon_id",
        "amount_today",
        "success_url",
        "cancel_url",
    }


async def test_consent_and_customer_are_stored_before_the_stripe_checkout_call(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session = await _with_plan(uow, clock, content)
    await _checkout(uow, clock, content, gateway).execute(session, True, None)
    stored = await uow.subscriptions.get(session.id)
    assert stored is not None
    assert stored.status == "none"
    assert stored.auto_renew_consent_at == clock.now()
    assert stored.stripe_customer_id == "cus_fake_1"
    assert uow.subscriptions.saves[0].stripe_customer_id is None  # consent saved first


async def test_second_checkout_reuses_the_customer(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session = await _with_plan(uow, clock, content)
    use_case = _checkout(uow, clock, content, gateway)
    await use_case.execute(session, True, None)
    await use_case.execute(session, True, None)
    assert len(gateway.customers) == 1 and len(gateway.checkout_requests) == 2
    assert {r.customer_id for r in gateway.checkout_requests} == {"cus_fake_1"}


async def test_checkout_when_already_subscribed_raises(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session = await _with_plan(uow, clock, content)
    from app.application.billing.dto import StartRequest

    await StartSubscription(uow, content, clock).execute(
        session, StartRequest("demo", auto_renew_consent=True)
    )
    with pytest.raises(AlreadySubscribed):
        await _checkout(uow, clock, content, gateway).execute(session, True, None)
    assert gateway.customers == []


async def test_gateway_error_propagates_after_consent_was_stored(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    gateway.fail_with = PaymentGatewayError()
    session = await _with_plan(uow, clock, content)
    with pytest.raises(PaymentGatewayError):
        await _checkout(uow, clock, content, gateway).execute(session, True, None)
    stored = await uow.subscriptions.get(session.id)
    assert stored is not None and stored.status == "none"


async def _paid(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,
    gateway: FakePaymentGateway,
    offset: timedelta = timedelta(0),
) -> tuple[Session, str]:
    session = await _with_plan(uow, clock, content, offset=offset)
    ref = await _checkout(uow, clock, content, gateway).execute(session, True, None)
    gateway.pay(ref.id)
    return session, ref.id


async def test_reconcile_paid_session_moves_status_to_active_and_creates_schedule_purges_q3_q5(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session, checkout_id = await _paid(uow, clock, content, gateway)
    result = await _reconcile(uow, clock, content, gateway).execute(session, checkout_id)
    assert result.paid
    sub = await uow.subscriptions.get(session.id)
    assert sub is not None
    assert (sub.status, sub.source, sub.plan_id) == ("active", "stripe", "four_week")
    assert sub.current_period_end == gateway.period_end
    assert (sub.stripe_customer_id, sub.stripe_subscription_id) == (
        "cus_fake_1",
        f"sub_fake_{checkout_id}",
    )
    [entry] = await uow.subscription_history.list_for_session(session.id)
    assert (entry.from_status, entry.to_status, entry.source) == ("none", "active", "stripe")
    quiz = await uow.quiz.get(session.id)
    assert quiz is not None and quiz.locked and quiz.health_answers_purged_at is not None
    assert "q3_situation" not in quiz.answers and "q5_changes" not in quiz.answers
    assert await uow.lesson_schedule.list_for_session(session.id)


async def test_reconcile_unpaid_session_leaves_status_and_returns_no_payment_message(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session = await _with_plan(uow, clock, content)
    ref = await _checkout(uow, clock, content, gateway).execute(session, True, None)
    result = await _reconcile(uow, clock, content, gateway).execute(session, ref.id)
    assert not result.paid and result.subscription.status == "none"
    assert uow.subscription_history.entries == []
    quiz = await uow.quiz.get(session.id)
    assert quiz is not None and not quiz.locked
    assert await uow.lesson_schedule.list_for_session(session.id) == []


async def test_reconcile_twice_starts_subscription_once(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session, checkout_id = await _paid(uow, clock, content, gateway)
    reconcile = _reconcile(uow, clock, content, gateway)
    await reconcile.execute(session, checkout_id)
    schedule = await uow.lesson_schedule.list_for_session(session.id)
    saves = len(uow.subscriptions.saves)
    clock.advance(timedelta(days=1))
    second = await reconcile.execute(session, checkout_id)
    assert second.paid and second.subscription.status == "active"
    assert len(await uow.subscription_history.list_for_session(session.id)) == 1
    assert await uow.lesson_schedule.list_for_session(session.id) == schedule
    assert len(uow.subscriptions.saves) == saves


async def test_reconcile_of_another_sessions_checkout_is_not_found(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    _, checkout_id = await _paid(uow, clock, content, gateway)
    other = Session(uuid4(), "h2", "UTC", timedelta(0), clock.now(), clock.now())
    with pytest.raises(CheckoutNotFound):
        await _reconcile(uow, clock, content, gateway).execute(other, checkout_id)


async def test_reconcile_without_period_end_falls_back_to_intro_period(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    gateway = FakePaymentGateway()
    session, checkout_id = await _paid(uow, clock, content, gateway)
    info = gateway.sessions[checkout_id]
    gateway.sessions[checkout_id] = type(info)(**{**info.__dict__, "period_end": None})
    result = await _reconcile(uow, clock, content, gateway).execute(session, checkout_id)
    assert result.subscription.current_period_end == clock.now() + timedelta(days=28)
