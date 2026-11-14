import logging
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.care_card.entities import SNAPSHOT_KEYS
from app.infrastructure.rate_limit import InMemoryRateLimiter
from tests.fakes.clock import FixedClock
from tests.presentation.test_lessons_api import pclient, subscribe  # noqa: F401

PROFILE: dict[str, Any] = {
    "displayName": "Margaret",
    "enjoys": ["old songs"],
    "calms": ["a cup of tea"],
    "avoid": ["loud rooms"],
    "rhythm": "Up at 7, nap at 2.",
    "contacts": [{"name": "Sam", "phone": "+1 (555) 123-4567", "role": "neighbour"}],
    "caregiverFirstName": "Alex",
}


@pytest.fixture
async def public(db_app: FastAPI, pclient: httpx.AsyncClient) -> AsyncIterator[httpx.AsyncClient]:  # noqa: F811
    """A client with no session token."""
    transport = httpx.ASGITransport(app=db_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def phrase(client: httpx.AsyncClient, body: str) -> str:
    r = await client.post("/api/phrases", json={"text": body, "source": "scenario"})
    assert r.status_code in (200, 201), r.text
    return str(r.json()["id"])


async def test_routes_behind_gate_but_public_route_needs_no_session(
    pclient: httpx.AsyncClient,  # noqa: F811
    public: httpx.AsyncClient,
) -> None:
    for method in ("get", "post", "put", "delete"):
        assert (await getattr(pclient, method)("/api/care-card")).status_code == 402
    assert (await public.get("/api/cards/unknown")).status_code == 404


async def test_preview_before_publishing(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    await pclient.put("/api/profile", json=PROFILE)
    pid = await phrase(pclient, "I am here.")
    body = (await pclient.get("/api/care-card")).json()
    assert body["status"] == "not_published" and body["link"] is None
    assert body["published"] is None and body["newPhraseCount"] == 0
    assert body["preview"]["displayName"] == "Margaret" and body["preview"]["phrases"] == []
    assert [p["id"] for p in body["availablePhrases"]] == [pid]
    assert [h["phone"] for h in body["preview"]["helplines"]][:2] == ["911", "988"]


async def test_card_id_at_least_16_chars_urlsafe(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.post("/api/care-card", json={})
    assert r.status_code == 200, r.text
    link = r.json()["link"]
    assert link.startswith("http://localhost:3000/card/")
    card_id = link.rsplit("/", 1)[1]
    assert len(card_id) >= 16
    assert all(c.isalnum() or c in "-_" for c in card_id)


async def test_public_get_without_session_returns_snapshot_and_sets_last_opened(
    pclient: httpx.AsyncClient,  # noqa: F811
    public: httpx.AsyncClient,
    db_app: FastAPI,
) -> None:
    await subscribe(pclient)
    await pclient.put("/api/profile", json=PROFILE)
    chosen = await phrase(pclient, "I am here.")
    await phrase(pclient, "Not chosen")
    published = (await pclient.post("/api/care-card", json={"phraseIds": [chosen]})).json()
    assert published["status"] == "published" and published["lastOpenedAt"] is None
    card_id = published["link"].rsplit("/", 1)[1]
    r = await public.get(f"/api/cards/{card_id}")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert set(body) == SNAPSHOT_KEYS
    assert body["displayName"] == "Margaret" and body["phrases"] == ["I am here."]
    assert body["calms"] == ["a cup of tea"] and body["caregiverFirstName"] == "Alex"
    assert body["contacts"] == [{"name": "Sam", "phone": "+1 (555) 123-4567", "role": "neighbour"}]
    assert body["helplines"] and body["updatedOn"] == db_app.state.clock.now().date().isoformat()
    assert (await pclient.get("/api/care-card")).json()["lastOpenedAt"] is not None


async def test_snapshot_never_contains_quiz_answers_diagnosis_or_medications(
    pclient: httpx.AsyncClient,  # noqa: F811
    public: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await subscribe(pclient)  # the quiz answers (persona B) exist for this session
    extra = {**PROFILE, "diagnosis": "DIAG-SECRET", "medications": ["MED-SECRET"]}
    assert (await pclient.put("/api/profile", json=extra)).status_code == 422
    await pclient.put("/api/profile", json=PROFILE)
    await pclient.put(
        "/api/visit-sheet", json={"doctor": "VISIT-SECRET", "familyNotes": "VISIT-SECRET"}
    )
    bad = await pclient.post("/api/care-card", json={"phraseIds": [], "diagnosis": "DIAG-SECRET"})
    assert bad.status_code == 422
    published = (await pclient.post("/api/care-card", json={})).json()
    card_id = published["link"].rsplit("/", 1)[1]
    body = (await public.get(f"/api/cards/{card_id}")).json()
    assert set(body) == SNAPSHOT_KEYS
    assert "SECRET" not in repr(body)
    async with session_factory() as db:
        stored = (await db.execute(text("SELECT snapshot::text FROM care_cards"))).scalar_one()
    assert "SECRET" not in stored
    quiz = (await pclient.get("/api/quiz")).json()
    assert quiz  # quiz answers exist but none of their values are in the public shape


async def test_publish_with_phrase_ids_of_another_session_rejected_422(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await subscribe(pclient)
    other = httpx.AsyncClient(transport=httpx.ASGITransport(app=db_app), base_url="http://test")
    async with other:
        other.headers["X-Session-Token"] = (await other.post("/api/session")).json()["token"]
        await subscribe(other)
        theirs = await phrase(other, "Theirs")
    r = await pclient.post("/api/care-card", json={"phraseIds": [theirs]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_card_phrases"
    assert (await pclient.get("/api/care-card")).json()["status"] == "not_published"


async def test_publish_twice_409_update_without_card_409(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    assert (await pclient.put("/api/care-card", json={})).status_code == 409
    assert (await pclient.delete("/api/care-card")).status_code == 409
    assert (await pclient.post("/api/care-card", json={})).status_code == 200
    assert (await pclient.post("/api/care-card", json={})).status_code == 409


async def test_update_resnapshots_under_same_id(
    pclient: httpx.AsyncClient,  # noqa: F811
    public: httpx.AsyncClient,
) -> None:
    await subscribe(pclient)
    await pclient.put("/api/profile", json=PROFILE)
    first = (await pclient.post("/api/care-card", json={})).json()["link"]
    await pclient.put("/api/profile", json={**PROFILE, "calms": ["quiet music"]})
    pid = await phrase(pclient, "New phrase")
    second = (await pclient.put("/api/care-card", json={"phraseIds": [pid]})).json()
    assert second["link"] == first and second["status"] == "published"
    body = (await public.get(f"/api/cards/{first.rsplit('/', 1)[1]}")).json()
    assert body["calms"] == ["quiet music"] and body["phrases"] == ["New phrase"]


async def test_status_update_available_after_profile_change(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await subscribe(pclient)
    await pclient.put("/api/profile", json=PROFILE)
    pid = await phrase(pclient, "Keep me")
    await pclient.post("/api/care-card", json={"phraseIds": [pid]})
    assert (await pclient.get("/api/care-card")).json()["status"] == "published"
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(hours=1))
    await phrase(pclient, "Saved later")
    got = (await pclient.get("/api/care-card")).json()
    assert got["status"] == "published" and got["newPhraseCount"] == 1
    await pclient.put("/api/profile", json={**PROFILE, "rhythm": "Changed"})
    assert (await pclient.get("/api/care-card")).json()["status"] == "update_available"
    await pclient.put("/api/care-card", json={"phraseIds": [pid]})
    assert (await pclient.get("/api/care-card")).json()["status"] == "published"
    assert (await pclient.delete(f"/api/phrases/{pid}")).status_code == 204
    assert (await pclient.get("/api/care-card")).json()["status"] == "update_available"


async def test_revoked_card_returns_410_this_card_is_no_longer_shared(
    pclient: httpx.AsyncClient,  # noqa: F811
    public: httpx.AsyncClient,
) -> None:
    await subscribe(pclient)
    link = (await pclient.post("/api/care-card", json={})).json()["link"]
    card_id = link.rsplit("/", 1)[1]
    revoked = (await pclient.delete("/api/care-card")).json()
    assert revoked["status"] == "revoked" and revoked["link"] is None
    r = await public.get(f"/api/cards/{card_id}")
    assert r.status_code == 410
    assert r.json()["error"]["message"] == "This card is no longer shared."
    again = (await pclient.post("/api/care-card", json={})).json()
    assert again["link"] != link and again["status"] == "published"
    assert (await public.get(f"/api/cards/{card_id}")).status_code == 410


async def test_revoke_deletes_snapshot_data_keeps_tombstone(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await subscribe(pclient)
    await pclient.put("/api/profile", json=PROFILE)
    pid = await phrase(pclient, "A phrase")
    await pclient.post("/api/care-card", json={"phraseIds": [pid]})
    await pclient.delete("/api/care-card")
    async with session_factory() as db:
        rows = (
            await db.execute(
                text("SELECT id, session_id, snapshot, phrase_ids, revoked_at FROM care_cards")
            )
        ).all()
    assert len(rows) == 1
    _, session_id, snapshot, phrase_ids, revoked_at = rows[0]
    assert session_id is not None and snapshot is None and phrase_ids == []
    assert revoked_at is not None


async def test_unknown_id_404(public: httpx.AsyncClient) -> None:
    r = await public.get("/api/cards/not-a-real-card-id-0000")
    assert r.status_code == 404 and r.json()["error"]["code"] == "card_not_found"


async def test_session_delete_cascades_card_and_tombstone_so_id_returns_404(
    pclient: httpx.AsyncClient,  # noqa: F811
    public: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await subscribe(pclient)
    live = (await pclient.post("/api/care-card", json={})).json()["link"].rsplit("/", 1)[1]
    await pclient.delete("/api/care-card")
    live2 = (await pclient.post("/api/care-card", json={})).json()["link"].rsplit("/", 1)[1]
    assert (await public.get(f"/api/cards/{live}")).status_code == 410
    async with session_factory() as db:
        await db.execute(text("DELETE FROM sessions"))
        await db.commit()
        assert (await db.execute(text("SELECT count(*) FROM care_cards"))).scalar_one() == 0
    assert (await public.get(f"/api/cards/{live}")).status_code == 404
    assert (await public.get(f"/api/cards/{live2}")).status_code == 404


async def test_public_route_rate_limited_429(
    public: httpx.AsyncClient,
    db_app: FastAPI,
) -> None:
    db_app.state.card_rate_limiter = InMemoryRateLimiter(3, timedelta(minutes=1))
    codes = [(await public.get("/api/cards/unknown-card-id-000000")).status_code for _ in range(5)]
    assert codes == [404, 404, 404, 429, 429]
    r = await public.get("/api/cards/unknown-card-id-000000")
    assert r.json()["error"]["code"] == "rate_limited"


async def test_card_text_never_appears_in_logs(
    pclient: httpx.AsyncClient,  # noqa: F811
    public: httpx.AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await subscribe(pclient)
    caplog.set_level(logging.DEBUG)
    await pclient.put(
        "/api/profile", json={**PROFILE, "rhythm": "ZEBRA-RHYTHM", "calms": ["ZEBRA-CALM"]}
    )
    pid = await phrase(pclient, "ZEBRA-PHRASE")
    link = (await pclient.post("/api/care-card", json={"phraseIds": [pid]})).json()["link"]
    assert (await public.get(f"/api/cards/{link.rsplit('/', 1)[1]}")).status_code == 200
    await pclient.put("/api/care-card", json={"phraseIds": [pid]})
    await pclient.get("/api/care-card")
    await pclient.delete("/api/care-card")
    logs = " ".join(r.getMessage() + repr(r.__dict__) for r in caplog.records)
    assert any(r.name == "app.request" for r in caplog.records)
    assert "ZEBRA" not in logs
