from datetime import timedelta
from uuid import uuid4

from app.application.profile.use_cases import GetProfile, ProfileInput, UpdateProfile
from app.domain.profile.entities import Contact
from app.domain.session.entities import Session
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork


def data(**changes: object) -> ProfileInput:
    base = ProfileInput(
        "Margaret",
        ("music",),
        ("tea",),
        ("crowds",),
        "Up at 7",
        (Contact("Sam", "555 123 4567", "neighbour"),),
        "Alex",
    )
    return ProfileInput(**{**base.__dict__, **changes})


async def _session(uow: FakeUnitOfWork, clock: FixedClock) -> Session:
    now = clock.now()
    session = Session(uuid4(), uuid4().hex, "UTC", timedelta(0), now, now)
    await uow.sessions.add(session)
    return session


async def test_get_without_profile_is_empty_and_not_stored(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    session = await _session(uow, clock)
    view = await GetProfile(uow, clock).execute(session)
    assert not view.exists and view.profile.calms == () and view.display_name is None
    assert uow.profiles.rows == {}


async def test_update_stores_profile_and_display_name_on_the_session(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    session = await _session(uow, clock)
    view = await UpdateProfile(uow, clock).execute(session, data())
    assert view.exists and view.display_name == "Margaret"
    assert uow.committed
    stored = await uow.sessions.get(session.id)
    assert stored is not None and stored.display_name == "Margaret"
    assert uow.profiles.rows[session.id].calms == ("tea",)
    again = await GetProfile(uow, clock).execute(session)
    assert again.profile == view.profile


async def test_null_display_name_clears_it(uow: FakeUnitOfWork, clock: FixedClock) -> None:
    session = await _session(uow, clock)
    await UpdateProfile(uow, clock).execute(session, data())
    view = await UpdateProfile(uow, clock).execute(session, data(display_name=None))
    assert view.display_name is None and session.display_name is None
