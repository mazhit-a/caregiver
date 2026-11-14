from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.demo.renewals import RollDemoRenewals
from app.application.demo.use_cases import AdvanceDemoDay, JumpToRenewal
from app.application.session.use_cases import ResolveSession
from app.domain.billing.entities import Subscription, SubscriptionSource, SubscriptionStatus
from app.domain.session.entities import Session
from app.domain.session.tokens import hash_token
from app.infrastructure.content.provider import JsonContentProvider
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork

REPO = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def content() -> JsonContentProvider:
    return JsonContentProvider.from_directory(REPO / "content")


async def _setup(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    status: SubscriptionStatus = "demo",
    source: SubscriptionSource = "demo",
) -> Session:
    session = Session(uuid4(), hash_token("t"), "UTC", timedelta(0), clock.now(), clock.now())
    await uow.sessions.add(session)
    await uow.subscriptions.save(
        Subscription(
            session.id,
            status=status,
            plan_id="four_week",
            source=source,
            current_period_start=clock.now(),
            current_period_end=clock.now() + timedelta(days=28),
            auto_renew_consent_at=clock.now(),
        )
    )
    return session


async def test_several_missed_periods_roll_in_one_call(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _setup(uow, clock)
    start = clock.now()
    now = start + timedelta(days=28 * 3 + 1)
    await RollDemoRenewals(uow, content).execute(session, now)
    sub = await uow.subscriptions.get(session.id)
    assert sub is not None
    assert sub.renewal_count == 3
    assert sub.current_period_end == start + timedelta(days=28 * 4)
    entries = await uow.subscription_history.list_for_session(session.id)
    assert [e.at for e in entries] == [start + timedelta(days=28 * i) for i in (1, 2, 3)]


async def test_no_roll_before_period_end(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _setup(uow, clock)
    await RollDemoRenewals(uow, content).execute(session, clock.now() + timedelta(days=27))
    sub = await uow.subscriptions.get(session.id)
    assert sub is not None and sub.renewal_count == 0
    assert await uow.subscription_history.list_for_session(session.id) == []


async def test_stripe_subscriptions_are_never_rolled_lazily(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _setup(uow, clock, status="active", source="stripe")
    await RollDemoRenewals(uow, content).execute(session, clock.now() + timedelta(days=60))
    sub = await uow.subscriptions.get(session.id)
    assert sub is not None and sub.renewal_count == 0


async def test_resolve_session_rolls_renewal(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _setup(uow, clock)
    clock.advance(timedelta(days=29))
    await ResolveSession(uow, clock, RollDemoRenewals(uow, content)).execute("t")
    sub = await uow.subscriptions.get(session.id)
    assert sub is not None and sub.renewal_count == 1


async def test_next_day_adds_24_hours_and_jump_sets_one_hour_after_period_end(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    session = await _setup(uow, clock)
    state = await AdvanceDemoDay(uow, clock).execute(session)
    assert state.clock_offset == timedelta(hours=24)
    state = await JumpToRenewal(uow, clock).execute(session)
    assert state.app_now == clock.now() + timedelta(days=28, hours=1)
    stored = await uow.sessions.get_by_token_hash(hash_token("t"))
    assert stored is not None and stored.clock_offset == timedelta(days=28, hours=1)
