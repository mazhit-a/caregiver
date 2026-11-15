import re

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.content.provider import JsonContentProvider
from tests.presentation.test_billing_api import (  # noqa: F401
    _answer_and_complete,
    _force_status,
    content,
    pclient,
)

IDS = ["qg_missing", "qg_fall", "qg_sudden_change", "qg_hospital", "qg_limit"]


def _no_braces(node: object) -> bool:
    if isinstance(node, str):
        return not re.search(r"[{}]", node)
    if isinstance(node, list):
        return all(_no_braces(n) for n in node)
    if isinstance(node, dict):
        return all(_no_braces(n) for n in node.values())
    return True


async def test_list_is_public_without_any_token(
    content: JsonContentProvider,  # noqa: F811
    db_client: httpx.AsyncClient,
) -> None:
    r = await db_client.get("/api/guides")
    assert r.status_code == 200, r.text
    guides = r.json()["guides"]
    assert [g["id"] for g in guides] == IDS
    assert set(guides[0]) == {"id", "title", "summary", "urgency"}
    assert guides[0]["title"] == "If your loved one goes missing"
    assert _no_braces(r.json())


async def test_guide_detail_is_public_and_complete(
    content: JsonContentProvider,  # noqa: F811
    db_client: httpx.AsyncClient,
) -> None:
    r = await db_client.get("/api/guides/qg_limit")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["urgency"] == "support"
    assert body["callNowTitle"] == "Call 911 now if"
    assert body["stepsTitle"] == "What to do"
    assert body["footer"] == "In an emergency, call 911."
    assert body["resources"][0] == {
        "label": body["resources"][0]["label"],
        "number": "988",
        "tel": "988",
    }
    assert body["sources"][0]["url"].startswith("https://")
    assert _no_braces(body)


async def test_unknown_guide_is_404_in_the_error_shape(
    content: JsonContentProvider,  # noqa: F811
    db_client: httpx.AsyncClient,
) -> None:
    r = await db_client.get("/api/guides/qg_nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "unknown_guide"


async def test_unknown_token_is_401_like_pricing(
    content: JsonContentProvider,  # noqa: F811
    db_client: httpx.AsyncClient,
) -> None:
    r = await db_client.get("/api/guides", headers={"X-Session-Token": "bogus"})
    assert r.status_code == 401


async def test_session_with_no_plan_gets_neutral_text(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    r = await pclient.get("/api/guides/qg_missing")
    assert r.status_code == 200
    assert r.json()["title"] == "If your loved one goes missing"


async def test_session_labels_are_used_for_the_recipient(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await _answer_and_complete(pclient)
    body = (await pclient.get("/api/guides/qg_fall")).json()
    assert _no_braces(body)
    assert "Mom" in body["callNow"][0] or "She" in body["callNow"][0]
    assert (await pclient.get("/api/guides")).json()["guides"][0]["title"] == "If Mom goes missing"


async def test_guides_need_no_subscription_even_when_past_due(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """No gate: a session with a plan but no subscription, and a past_due one, both read guides."""
    await _answer_and_complete(pclient)
    assert (await pclient.get("/api/guides/qg_hospital")).status_code == 200  # no subscription
    await _force_status(session_factory, "past_due")
    assert (await pclient.get("/api/guides/qg_hospital")).status_code == 200
    assert (await pclient.get("/api/guides")).status_code == 200
