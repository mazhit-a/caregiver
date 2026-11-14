import re

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.presentation.test_billing_api import (  # noqa: F401
    _answer_and_complete,
    _force_status,
    content,
    pclient,
)


def _clean(body: dict[str, dict[str, str]]) -> bool:
    texts = [t for section in body.values() for t in section.values()]
    return bool(texts) and not any(re.search(r"[{}]|\*\*", t) for t in texts)


async def test_app_copy_requires_a_session(db_client: httpx.AsyncClient) -> None:
    assert (await db_client.get("/api/app-copy")).status_code == 401


async def test_app_copy_works_before_the_quiz_with_neutral_labels(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    r = await pclient.get("/api/app-copy")
    assert r.status_code == 200, r.text
    assert _clean(r.json())
    assert r.json()["nav"]["profilePage"] == "Your loved one's page"


async def test_app_copy_is_finished_text_for_the_recipient(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await _answer_and_complete(pclient)
    r = await pclient.get("/api/app-copy")
    assert r.status_code == 200, r.text
    body = r.json()
    assert _clean(body)
    assert body["nav"]["profilePage"] == "Mom's page"
    assert body["plan"]["title"] == "Mom's course"
    assert body["settings"]["gentleExitEntry"] == "Mom has passed away or moved to a care facility"
    assert body["careCard"]["sharingSentence"].startswith("Anyone who has the link")


async def test_app_copy_works_when_payment_is_past_due(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _answer_and_complete(pclient)
    await _force_status(session_factory, "past_due")
    assert (await pclient.get("/api/app-copy")).status_code == 200


async def test_app_copy_follows_the_display_name(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _answer_and_complete(pclient)
    async with session_factory() as db:
        await db.execute(text("UPDATE sessions SET display_name = 'Margaret'"))
        await db.commit()
    body = (await pclient.get("/api/app-copy")).json()
    assert body["nav"]["profilePage"] == "Margaret's page"
    assert body["profile"]["worksTitle"] == "What works with Margaret"
    assert _clean(body)


async def test_app_copy_writes_nothing(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _answer_and_complete(pclient)

    async def snapshot() -> tuple[object, ...]:
        async with session_factory() as db:
            rows = await db.execute(
                text(
                    "SELECT (SELECT count(*) FROM sessions), (SELECT count(*) FROM plans),"
                    " (SELECT count(*) FROM subscriptions), (SELECT count(*) FROM profiles)"
                )
            )
            return tuple(rows.one())

    before = await snapshot()
    assert (await pclient.get("/api/app-copy")).status_code == 200
    assert await snapshot() == before
