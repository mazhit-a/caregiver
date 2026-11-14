import logging
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI

from app.domain.visit_sheet.entities import (
    MAX_CUSTOM_QUESTION_LENGTH,
    MAX_CUSTOM_QUESTIONS,
    MAX_FAMILY_NOTES_LENGTH,
)
from tests.presentation.test_checkins_api import make_plan
from tests.presentation.test_lessons_api import pclient, subscribe  # noqa: F401

FOOTER = "Family observations, not a medical assessment."


async def test_requires_subscription_402(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    assert (await pclient.get("/api/visit-sheet")).status_code == 402
    assert (await pclient.put("/api/visit-sheet", json={})).status_code == 402


async def test_empty_get_has_bank_and_footer(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.get("/api/visit-sheet")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["questions"] == [] and body["suggestedNotes"] == []
    assert body["footer"] == FOOTER and len(body["bank"]) == 8


async def test_put_get_roundtrip_keeps_question_order(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    put = {
        "doctor": "Dr. Lee",
        "visitDate": "2026-12-01",
        "familyNotes": "Asked the same thing 6 times.",
        "questions": [
            {"text": "Is the new walker right?"},
            {"id": "q_safety"},
            {"id": "q_changes"},
            {"text": "Second of mine"},
        ],
    }
    r = await pclient.put("/api/visit-sheet", json=put)
    assert r.status_code == 200, r.text
    got = (await pclient.get("/api/visit-sheet")).json()
    assert got["doctor"] == "Dr. Lee" and got["visitDate"] == "2026-12-01"
    assert got["familyNotes"] == "Asked the same thing 6 times."
    assert [(q["id"], q["custom"]) for q in got["questions"]] == [
        (None, True),
        ("q_safety", False),
        ("q_changes", False),
        (None, True),
    ]
    assert got["questions"][1]["text"].startswith("Is there anything at home")
    assert got["footer"] == FOOTER
    # a second PUT replaces the whole sheet
    r = await pclient.put("/api/visit-sheet", json={"questions": [{"id": "q_changes"}]})
    assert [q["id"] for q in r.json()["questions"]] == ["q_changes"]
    assert r.json()["doctor"] is None


async def test_bank_question_ids_validated_unknown_id_422(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.put("/api/visit-sheet", json={"questions": [{"id": "q_made_up"}]})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unknown_visit_question"
    assert r.json()["error"]["details"] == {"questionIds": ["q_made_up"]}
    assert (await pclient.get("/api/visit-sheet")).json()["questions"] == []


async def test_custom_questions_cap_and_length_422(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    too_many = [{"text": f"q{i}"} for i in range(MAX_CUSTOM_QUESTIONS + 1)]
    r = await pclient.put("/api/visit-sheet", json={"questions": too_many})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_visit_sheet"
    long = {"questions": [{"text": "x" * (MAX_CUSTOM_QUESTION_LENGTH + 1)}]}
    r = await pclient.put("/api/visit-sheet", json=long)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = await pclient.put(
        "/api/visit-sheet", json={"familyNotes": "x" * (MAX_FAMILY_NOTES_LENGTH + 1)}
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    both = {"questions": [{"id": "q_changes", "text": "x"}]}
    assert (await pclient.put("/api/visit-sheet", json=both)).status_code == 422
    ok = [{"text": f"q{i}"} for i in range(MAX_CUSTOM_QUESTIONS)]
    assert (await pclient.put("/api/visit-sheet", json={"questions": ok})).status_code == 200


async def test_observations_from_checkin_appear_as_suggested_notes(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await make_plan(pclient)
    db_app.state.clock.advance(timedelta(days=1))
    r = await pclient.post(
        "/api/checkins",
        json={
            "planId": "m1_l1",
            "cameUp": "yes",
            "outcome": "helped",
            "doctorNote": {"addToVisitSheet": True, "text": "At dinner"},
        },
    )
    assert r.status_code == 200, r.text
    notes = (await pclient.get("/api/visit-sheet")).json()["suggestedNotes"]
    assert [n["text"] for n in notes] == ["At dinner"]


async def test_not_added_observation_is_not_suggested(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await make_plan(pclient)
    db_app.state.clock.advance(timedelta(days=1))
    body = {"planId": "m1_l1", "cameUp": "yes", "outcome": "helped"}
    r = await pclient.post(
        "/api/checkins", json={**body, "doctorNote": {"addToVisitSheet": False, "text": "Skip"}}
    )
    assert r.status_code == 200, r.text
    assert (await pclient.get("/api/visit-sheet")).json()["suggestedNotes"] == []


async def test_footer_text_always_present(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    for call in (
        pclient.get("/api/visit-sheet"),
        pclient.put("/api/visit-sheet", json={"familyNotes": "x"}),
    ):
        assert (await call).json()["footer"] == FOOTER


async def test_visit_sheet_not_in_care_card_snapshot_or_any_public_route(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await subscribe(pclient)
    await pclient.put("/api/visit-sheet", json={"familyNotes": "SECRET-NOTE-TEXT"})
    schema_paths = list(db_app.openapi()["paths"])
    assert [p for p in schema_paths if "visit" in p] == ["/api/visit-sheet"]
    assert not [p for p in schema_paths if p.startswith("/api/cards") and "visit" in p]
    # no token, no data: the only route that serves the sheet is gated
    anonymous = httpx.AsyncClient(transport=httpx.ASGITransport(app=db_app), base_url="http://test")
    async with anonymous as c:
        assert (await c.get("/api/visit-sheet")).status_code == 401
        for path in ("/api/cards/anything", "/api/cards/anything/visit-sheet"):
            r = await c.get(path)
            assert "SECRET-NOTE-TEXT" not in r.text and "visit" not in r.text.lower()


async def test_note_text_never_appears_in_logs(
    pclient: httpx.AsyncClient,  # noqa: F811
    caplog: pytest.LogCaptureFixture,
) -> None:
    await subscribe(pclient)
    caplog.set_level(logging.DEBUG)
    secret = "ZEBRA-QUOKKA-9137"
    await pclient.put(
        "/api/visit-sheet",
        json={"doctor": secret, "familyNotes": secret, "questions": [{"text": secret}]},
    )
    await pclient.put(  # rejected: unknown id and over-long notes
        "/api/visit-sheet",
        json={"familyNotes": secret * 400, "questions": [{"id": secret}]},
    )
    await pclient.put("/api/visit-sheet", json={"questions": [{"id": secret}]})
    await pclient.get("/api/visit-sheet")
    assert secret not in caplog.text
