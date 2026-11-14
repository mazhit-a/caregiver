from datetime import UTC, date, datetime, timedelta

import pytest

from app.application.session.use_cases import CreateSession, ResolveSession
from app.domain.session.errors import InvalidSessionToken, InvalidTimezone
from app.domain.session.tokens import hash_token
from tests.fakes.clock import FixedClock
from tests.fakes.sessions import FakeIdGenerator, FakeTokenGenerator
from tests.fakes.unit_of_work import FakeUnitOfWork


async def test_create_session_stores_only_the_hash_and_defaults_timezone(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    created = await CreateSession(
        uow, FakeTokenGenerator(["tok"]), FakeIdGenerator(), clock
    ).execute(None)
    stored = uow.sessions.rows[created.session.id]
    assert created.token == "tok"
    assert stored.token_hash == hash_token("tok")
    assert "tok" not in vars(stored).values()
    assert stored.timezone == "America/New_York"
    assert uow.committed


async def test_create_session_rejects_invalid_timezone(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    use_case = CreateSession(uow, FakeTokenGenerator(), FakeIdGenerator(), clock)
    with pytest.raises(InvalidTimezone):
        await use_case.execute("Nowhere/Land")
    assert not uow.sessions.rows


async def test_resolve_touches_last_seen_in_app_time_and_records_day_once(
    uow: FakeUnitOfWork,
) -> None:
    clock = FixedClock(datetime(2026, 1, 5, 15, 0, tzinfo=UTC))
    created = await CreateSession(
        uow, FakeTokenGenerator(["tok"]), FakeIdGenerator(), clock
    ).execute("America/New_York")
    resolve = ResolveSession(uow, clock)
    clock.advance(timedelta(hours=1))
    await resolve.execute("tok")
    await resolve.execute("tok")
    assert uow.sessions.rows[created.session.id].last_seen_at == clock.now()
    assert await uow.active_days.list_days(created.session.id) == [date(2026, 1, 5)]


async def test_resolve_rejects_missing_and_wrong_token(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    resolve = ResolveSession(uow, clock)
    for token in (None, "", "nope"):
        with pytest.raises(InvalidSessionToken):
            await resolve.execute(token)


async def test_resolve_exposes_the_previous_last_seen_before_updating_it(
    uow: FakeUnitOfWork,
) -> None:
    clock = FixedClock(datetime(2026, 1, 5, 15, 0, tzinfo=UTC))
    created = await CreateSession(
        uow, FakeTokenGenerator(["tok"]), FakeIdGenerator(), clock
    ).execute(None)
    resolve = ResolveSession(uow, clock)
    first_visit = clock.now()
    clock.advance(timedelta(days=7))
    session = await resolve.execute("tok")
    assert session.previous_last_seen_at == first_visit
    assert session.last_seen_at == clock.now()
    assert created.session.id == session.id
