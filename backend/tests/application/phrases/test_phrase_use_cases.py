from datetime import timedelta
from uuid import uuid4

import pytest

from app.application.phrases.use_cases import DeletePhrase, ListPhrases, SavePhrase
from app.domain.phrases.entities import MAX_PHRASES_PER_SESSION
from app.domain.phrases.errors import InvalidPhrase, PhraseLimitReached, PhraseNotFound
from app.domain.session.entities import Session
from tests.fakes.clock import FixedClock
from tests.fakes.sessions import FakeIdGenerator
from tests.fakes.unit_of_work import FakeUnitOfWork


def make_session(clock: FixedClock) -> Session:
    return Session(uuid4(), "h", "UTC", timedelta(0), clock.now(), clock.now())


async def test_save_phrase_then_list_then_delete(uow: FakeUnitOfWork, clock: FixedClock) -> None:
    session = make_session(clock)
    saved = await SavePhrase(uow, FakeIdGenerator(), clock).execute(
        session, "I'm here with you.", "scenario", "m1_l1"
    )
    listed = await ListPhrases(uow).execute(session)
    assert [p.text for p in listed] == ["I'm here with you."]
    assert listed[0].lesson_id == "m1_l1" and listed[0].saved_at == clock.now()
    await DeletePhrase(uow).execute(session, saved.id)
    assert await ListPhrases(uow).execute(session) == []


async def test_phrase_cap_per_session_rejected_with_message(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    session = make_session(clock)
    save = SavePhrase(uow, FakeIdGenerator(), clock)
    for i in range(MAX_PHRASES_PER_SESSION):
        await save.execute(session, f"phrase {i}", "roleplay", None)
    with pytest.raises(PhraseLimitReached) as error:
        await save.execute(session, "one more", "roleplay", None)
    assert "Remove one" in error.value.message
    other = make_session(clock)  # the cap is per session
    await save.execute(other, "mine", "gift", None)


async def test_blank_phrase_rejected(uow: FakeUnitOfWork, clock: FixedClock) -> None:
    with pytest.raises(InvalidPhrase):
        await SavePhrase(uow, FakeIdGenerator(), clock).execute(
            make_session(clock), "  ", "gift", None
        )


async def test_delete_other_sessions_phrase_is_not_found(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    owner, intruder = make_session(clock), make_session(clock)
    saved = await SavePhrase(uow, FakeIdGenerator(), clock).execute(owner, "mine", "gift", None)
    with pytest.raises(PhraseNotFound):
        await DeletePhrase(uow).execute(intruder, saved.id)
    assert len(await ListPhrases(uow).execute(owner)) == 1
