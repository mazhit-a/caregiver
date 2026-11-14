from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from app.application.care_card.use_cases import (
    GetCareCard,
    GetPublicCard,
    PublishCareCard,
    RevokeCareCard,
    UpdateCareCard,
)
from app.domain.care_card.errors import (
    CardAlreadyPublished,
    CardNotFound,
    CardNotPublished,
    CardRateLimited,
    CardRevoked,
    InvalidCardPhrases,
)
from app.domain.phrases.entities import SavedPhrase
from app.domain.profile.entities import Profile
from app.domain.safety.resources import CrisisResource
from app.domain.session.entities import Session
from app.domain.shared.labels import RecipientLabels
from app.infrastructure.rate_limit import InMemoryRateLimiter
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork


class StubContent:
    def recipient_labels(self, key: str) -> RecipientLabels:
        word = {"mom": "Mom", "other": "your loved one"}[key]
        return RecipientLabels(word, word + "'s", "she", "her", "was", "is", "has", "lives")

    def crisis_resources(self) -> list[CrisisResource]:
        return [CrisisResource("h", "Helpline", "988", "Call any time.")]


CONTENT = StubContent()


class SeqTokens:
    """Unique tokens across the whole test (publisher() builds a use case per call)."""

    count = 0

    def __init__(self, fixed: list[str] | None = None) -> None:
        self._fixed = fixed

    def new_token(self) -> str:
        if self._fixed:
            return self._fixed.pop(0)
        SeqTokens.count += 1
        return f"card-token-{SeqTokens.count:030d}"


async def setup(uow: FakeUnitOfWork, clock: FixedClock, **session: object) -> Session:
    now = clock.now()
    s = Session(uuid4(), uuid4().hex, "UTC", timedelta(0), now, now, **session)  # type: ignore[arg-type]
    await uow.sessions.add(s)
    return s


async def save_phrase(uow: FakeUnitOfWork, s: Session, clock: FixedClock, text: str) -> UUID:
    p = SavedPhrase(uuid4(), s.id, text, "scenario", None, clock.now())
    await uow.saved_phrases.add(p)
    return p.id


async def save_profile(uow: FakeUnitOfWork, s: Session, clock: FixedClock, **kw: object) -> None:
    base: dict[str, object] = dict(
        enjoys=["songs"], calms=["tea"], avoid=[], rhythm="r", contacts=[],
        caregiver_first_name="Alex",
    )  # fmt: skip
    await uow.profiles.save(
        Profile.create(s.id, updated_at=clock.now(), **(base | kw))  # type: ignore[arg-type]
    )


def publisher(
    uow: FakeUnitOfWork, clock: FixedClock, tokens: list[str] | None = None
) -> PublishCareCard:
    return PublishCareCard(uow, CONTENT, clock, SeqTokens(tokens))


async def test_publish_snapshots_profile_chosen_phrases_and_default_label(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    s = await setup(uow, clock, recipient_key="mom")
    a = await save_phrase(uow, s, clock, "A phrase")
    await save_phrase(uow, s, clock, "Not chosen")
    await save_profile(uow, s, clock)
    card = await publisher(uow, clock).execute(s, [a])
    snap = card.snapshot
    assert snap is not None and snap.phrases == ("A phrase",)
    assert snap.display_name == "Mom" and snap.enjoys == ("songs",)
    assert snap.helplines[0].phone == "988" and snap.caregiver_first_name == "Alex"
    assert uow.committed and len(card.id) >= 16


async def test_display_name_prefers_session_name_then_default_label(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    named = await setup(uow, clock, display_name="Margaret", recipient_key="mom")
    assert (await publisher(uow, clock).execute(named, [])).snapshot.display_name == "Margaret"  # type: ignore[union-attr]
    bare = await setup(uow, clock)
    assert (await publisher(uow, clock).execute(bare, [])).snapshot.display_name == (  # type: ignore[union-attr]
        "your loved one"
    )


async def test_session_extras_never_enter_the_snapshot(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    s = await setup(uow, clock, recipient_key="mom")
    await save_profile(uow, s, clock)
    card = await publisher(uow, clock).execute(s, [])
    assert card.snapshot is not None
    assert set(card.snapshot.to_json()) == {
        "displayName", "enjoys", "calms", "avoid", "rhythm", "contacts", "helplines",
        "phrases", "updatedOn", "caregiverFirstName",
    }  # fmt: skip


async def test_publish_with_phrase_ids_of_another_session_rejected(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    mine = await setup(uow, clock)
    other = await setup(uow, clock)
    theirs = await save_phrase(uow, other, clock, "Theirs")
    with pytest.raises(InvalidCardPhrases):
        await publisher(uow, clock).execute(mine, [theirs])
    with pytest.raises(InvalidCardPhrases):
        await publisher(uow, clock).execute(mine, [uuid4()])
    assert uow.care_cards.rows == {}


async def test_publish_twice_rejected_and_short_token_refused(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    s = await setup(uow, clock)
    await publisher(uow, clock).execute(s, [])
    with pytest.raises(CardAlreadyPublished):
        await publisher(uow, clock).execute(s, [])
    with pytest.raises(ValueError):
        await publisher(uow, clock, ["short"]).execute(await setup(uow, clock), [])


async def test_update_resnapshots_under_same_id(uow: FakeUnitOfWork, clock: FixedClock) -> None:
    s = await setup(uow, clock, recipient_key="mom")
    await save_profile(uow, s, clock, calms=["tea"])
    first = await publisher(uow, clock).execute(s, [])
    clock.advance(timedelta(days=1))
    await save_profile(uow, s, clock, calms=["music"])
    p = await save_phrase(uow, s, clock, "New one")
    second = await UpdateCareCard(uow, CONTENT, clock).execute(s, [p])
    assert second.id == first.id and second.published_at == first.published_at
    assert second.updated_at > first.updated_at
    assert second.snapshot is not None and second.snapshot.calms == ("music",)
    assert second.snapshot.phrases == ("New one",) and len(uow.care_cards.rows) == 1


async def test_update_or_revoke_without_live_card_rejected(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    s = await setup(uow, clock)
    with pytest.raises(CardNotPublished):
        await UpdateCareCard(uow, CONTENT, clock).execute(s, [])
    with pytest.raises(CardNotPublished):
        await RevokeCareCard(uow, clock).execute(s)
    await publisher(uow, clock).execute(s, [])
    await RevokeCareCard(uow, clock).execute(s)
    with pytest.raises(CardNotPublished):
        await UpdateCareCard(uow, CONTENT, clock).execute(s, [])


async def test_revoke_deletes_snapshot_data_keeps_tombstone_and_republish_gets_new_id(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    s = await setup(uow, clock)
    p = await save_phrase(uow, s, clock, "A")
    first = await publisher(uow, clock).execute(s, [p])
    await RevokeCareCard(uow, clock).execute(s)
    row = uow.care_cards.rows[first.id]
    assert row.snapshot is None and row.phrase_ids == () and row.revoked_at is not None
    view = await GetCareCard(uow, CONTENT, clock).execute(s)
    assert view.status == "revoked" and view.link_token is None and view.published is None
    second = await publisher(uow, clock).execute(s, [])
    assert second.id != first.id and uow.care_cards.rows[first.id].is_revoked
    assert (await GetCareCard(uow, CONTENT, clock).execute(s)).link_token == second.id


async def test_get_status_flow_and_new_phrase_count(uow: FakeUnitOfWork, clock: FixedClock) -> None:
    s = await setup(uow, clock, recipient_key="mom")
    get = GetCareCard(uow, CONTENT, clock)
    view = await get.execute(s)
    assert view.status == "not_published" and view.link_token is None
    assert view.preview.display_name == "Mom" and view.new_phrase_count == 0
    await publisher(uow, clock).execute(s, [])
    assert (await get.execute(s)).status == "published"
    clock.advance(timedelta(hours=1))
    await save_phrase(uow, s, clock, "later")
    view = await get.execute(s)
    assert view.status == "published" and view.new_phrase_count == 1
    await save_profile(uow, s, clock)
    assert (await get.execute(s)).status == "update_available"
    await UpdateCareCard(uow, CONTENT, clock).execute(s, [])
    assert (await get.execute(s)).status == "published"


async def test_public_get_records_last_opened_and_handles_missing_and_revoked(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    s = await setup(uow, clock)
    card = await publisher(uow, clock).execute(s, [])
    public = GetPublicCard(uow, clock, InMemoryRateLimiter(100))
    clock.advance(timedelta(hours=2))
    snap = await public.execute(card.id, "ip")
    assert snap == card.snapshot and uow.care_cards.rows[card.id].last_opened_at == clock.now()
    with pytest.raises(CardNotFound):
        await public.execute("nope", "ip")
    await RevokeCareCard(uow, clock).execute(s)
    with pytest.raises(CardRevoked):
        await public.execute(card.id, "ip")


async def test_public_get_is_rate_limited_per_client(
    uow: FakeUnitOfWork, clock: FixedClock
) -> None:
    public = GetPublicCard(uow, clock, InMemoryRateLimiter(2))
    for _ in range(2):
        with pytest.raises(CardNotFound):
            await public.execute("nope", "ip1")
    with pytest.raises(CardRateLimited):
        await public.execute("nope", "ip1")
    with pytest.raises(CardNotFound):
        await public.execute("nope", "ip2")
