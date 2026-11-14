import logging
from typing import Any

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.presentation.test_lessons_api import pclient, subscribe  # noqa: F401

FULL: dict[str, Any] = {
    "displayName": "Margaret",
    "enjoys": ["old songs", "gardening"],
    "calms": ["a cup of tea", "quiet music"],
    "avoid": ["loud rooms"],
    "rhythm": "Up at 7, nap at 2.",
    "contacts": [{"name": "Sam", "phone": "+1 (555) 123-4567", "role": "neighbour"}],
    "caregiverFirstName": "Alex",
}


async def test_profile_routes_require_the_subscription_gate(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    assert (await pclient.get("/api/profile")).status_code == 402
    assert (await pclient.put("/api/profile", json=FULL)).status_code == 402
    bare = await pclient.get("/api/profile", headers={"X-Session-Token": "nope"})
    assert bare.status_code == 401


async def test_get_before_any_put_is_empty(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    out = (await pclient.get("/api/profile")).json()
    assert out == {
        "displayName": None,
        "enjoys": [],
        "calms": [],
        "avoid": [],
        "rhythm": "",
        "contacts": [],
        "caregiverFirstName": None,
        "updatedAt": None,
    }


async def test_put_then_get_profile_roundtrip(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await subscribe(pclient)
    put = await pclient.put("/api/profile", json=FULL)
    assert put.status_code == 200, put.text
    got = (await pclient.get("/api/profile")).json()
    assert {k: v for k, v in got.items() if k != "updatedAt"} == FULL
    assert got["updatedAt"] is not None and got == put.json()
    replaced = await pclient.put("/api/profile", json={"calms": ["tea"]})
    assert replaced.json()["enjoys"] == [] and replaced.json()["displayName"] is None
    async with session_factory() as db:
        assert (await db.execute(text("SELECT count(*) FROM profiles"))).scalar_one() == 1
        await db.execute(text("DELETE FROM sessions"))
        await db.commit()
        assert (await db.execute(text("SELECT count(*) FROM profiles"))).scalar_one() == 0


@pytest.mark.parametrize("field", ["enjoys", "calms", "avoid"])
async def test_list_over_cap_422(pclient: httpx.AsyncClient, field: str) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.put("/api/profile", json={field: [f"item {i}" for i in range(11)]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = await pclient.put("/api/profile", json={"contacts": [FULL["contacts"][0]] * 6})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "body",
    [
        {"enjoys": ["x" * 81]},
        {"rhythm": "x" * 501},
        {"displayName": "x" * 81},
        {"caregiverFirstName": "x" * 41},
        {"contacts": [{"name": "x" * 61, "phone": "555 123 4567"}]},
    ],
)
async def test_string_over_length_422(pclient: httpx.AsyncClient, body: dict[str, Any]) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.put("/api/profile", json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


async def test_blank_item_and_bad_phone_422_in_the_shared_shape(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.put("/api/profile", json={"calms": ["  "]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_profile"
    r = await pclient.put("/api/profile", json={"contacts": [{"name": "Sam", "phone": "call"}]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_profile"
    assert set(r.json()["error"]) == {"code", "message", "details"}


@pytest.mark.parametrize("key", ["diagnosis", "medications", "doctor", "quizAnswers"])
async def test_unknown_field_rejected(pclient: httpx.AsyncClient, key: str) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.put("/api/profile", json={**FULL, key: "secret"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    nested = {**FULL, "contacts": [{"name": "Sam", "phone": "555 123 4567", key: "x"}]}
    assert (await pclient.put("/api/profile", json=nested)).status_code == 422


async def test_display_name_change_is_reflected_in_next_lesson_render(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    before = (await pclient.get("/api/lessons/m1_l1")).text
    assert "Zelda" not in before and "Mom" in before
    await pclient.put("/api/profile", json={"displayName": "Zelda"})
    after = (await pclient.get("/api/lessons/m1_l1")).text
    assert "Zelda's" in after and "When Zelda asks again" in after
    assert "{recipient}" not in after and "{possessive}" not in after
    await pclient.put("/api/profile", json={})
    assert "Zelda" not in (await pclient.get("/api/lessons/m1_l1")).text


async def test_profile_routes_do_not_log_body(
    pclient: httpx.AsyncClient,  # noqa: F811
    caplog: pytest.LogCaptureFixture,
) -> None:
    await subscribe(pclient)
    caplog.set_level(logging.DEBUG)
    body = {
        "displayName": "ZEBRA-NAME",
        "enjoys": ["ZEBRA-ENJOYS"],
        "calms": ["ZEBRA-CALMS"],
        "avoid": ["ZEBRA-AVOID"],
        "rhythm": "ZEBRA-RHYTHM",
        "contacts": [{"name": "ZEBRA-CONTACT", "phone": "555 123 4567"}],
        "caregiverFirstName": "ZEBRA-CG",
    }
    assert (await pclient.put("/api/profile", json=body)).status_code == 200
    assert (await pclient.get("/api/profile")).status_code == 200
    assert (
        await pclient.put("/api/profile", json={"rhythm": "ZEBRA-" + "x" * 600})
    ).status_code == 422
    logs = " ".join(r.getMessage() + repr(r.__dict__) for r in caplog.records)
    assert any(r.name == "app.request" for r in caplog.records)
    assert "ZEBRA" not in logs
