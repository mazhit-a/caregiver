"""HTTP hardening (increment 40): access log, body size, CORS, rate limits, error shapes, headers.

Rate limits: session creation per client address and events per session are in-memory limiters
(one process); role-play turns and the public card route have their own (tested next to them).
"""

import logging
from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.infrastructure.config import Settings
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.main import create_app
from tests.presentation.test_lessons_api import pclient, subscribe  # noqa: F401
from tests.presentation.test_roleplay_api import start, turn

CARD_ID = "cardIdBearerSecret-0123456789abcdef"


def _logged(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(f"{r.name} {r.getMessage()} {r.__dict__!r}" for r in caplog.records)


def _assert_error_shape(r: httpx.Response, status: int, code: str) -> None:
    assert r.status_code == status, r.text
    error = r.json()["error"]
    assert set(error) == {"code", "message", "details"}
    assert error["code"] == code


# --- access log ---------------------------------------------------------------------------------


async def test_public_card_id_appears_in_no_log_record(
    db_client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    r = await db_client.get(f"/api/cards/{CARD_ID}")
    assert r.status_code == 404
    access = [rec for rec in caplog.records if rec.name == "app.request"]
    assert access and "/api/cards/[redacted]" in access[0].getMessage()
    assert CARD_ID not in _logged(caplog)


async def test_access_log_has_no_query_string_or_body(
    db_client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await db_client.get("/api/health?token=QUERYSECRET&email=a@b.c")
    await db_client.post("/api/session", json={"timezone": "BODYSECRET/Zone"})
    logs = _logged(caplog)
    assert "QUERYSECRET" not in logs and "a@b.c" not in logs and "BODYSECRET" not in logs
    assert "GET /api/health -> 200" in logs


# --- request body size --------------------------------------------------------------------------


async def test_body_over_64kb_rejected_413_error_shape(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/session", content=b"{" + b" " * (64 * 1024 + 1) + b"}")
    _assert_error_shape(r, 413, "payload_too_large")
    assert r.json()["error"]["details"] == {"maxBytes": 64 * 1024}


async def test_streamed_body_over_64kb_without_content_length_rejected_413(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    @app.post("/api/_echo")
    async def echo(payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    async def chunks() -> Any:
        for _ in range(9):
            yield b" " * 8192  # 72 KB in total, no Content-Length (chunked)

    r = await client.post("/api/_echo", content=chunks())
    _assert_error_shape(r, 413, "payload_too_large")


async def test_body_at_the_limit_is_still_accepted(client: httpx.AsyncClient) -> None:
    # 413 is only for MORE than 64 KB; this one reaches the route (and fails field validation).
    r = await client.post("/api/session", content=b'{"timezone": "' + b"x" * 60000 + b'"}')
    assert r.status_code != 413


# --- field limits stay 422 ----------------------------------------------------------------------


async def test_request_field_over_limit_returns_422_error_shape(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    big = "xxxxxxxxxxxx" * 60  # 720 chars: over every text limit below, far under 64 KB
    quiz = await pclient.put("/api/quiz/answers/q2_age", json={"value": big})  # before the plan
    assert quiz.status_code == 422 and "xxxxxxxxxx" not in quiz.text
    assert set(quiz.json()["error"]) == {"code", "message", "details"}
    await subscribe(pclient)
    run = await start(pclient)
    cases: dict[str, tuple[str, str, dict[str, Any]]] = {
        "lessons": ("POST", "/api/lessons/m1_l1/answers", {"screenId": "s" * 65, "value": 1}),
        "phrases": ("POST", "/api/phrases", {"text": big, "source": "gift"}),
        "profile": ("PUT", "/api/profile", {"rhythm": big}),
        "visit_sheet": ("PUT", "/api/visit-sheet", {"familyNotes": big * 10}),
        "events": (
            "POST",
            "/api/events",
            {"events": [{"name": "landing_view", "props": {"source": big}}]},
        ),
        "roleplay": ("POST", f"/api/roleplay/{run['runId']}/turn", {"round": 1, "reply": big}),
    }
    for family, (method, path, body) in cases.items():
        r = await pclient.request(method, path, json=body)
        assert r.status_code in {413, 422}, family
        assert r.status_code == 422, (family, r.text)
        error = r.json()["error"]
        assert set(error) == {"code", "message", "details"}, family
        assert "xxxxxxxxxx" not in r.text, f"{family} echoes the request value"


# --- CORS ---------------------------------------------------------------------------------------


@pytest.fixture
async def cors_client() -> Any:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        stripe_secret_key="sk_test_dummy",
        anthropic_api_key="dummy",
        cors_origins="https://app.example.com, http://localhost:3000",
    )
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _preflight(client: httpx.AsyncClient, origin: str) -> Any:
    return client.options(
        "/api/session",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-session-token, content-type",
        },
    )


async def test_cors_allows_configured_origin_and_rejects_others(
    cors_client: httpx.AsyncClient,
) -> None:
    ok = await _preflight(cors_client, "https://app.example.com")
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == "https://app.example.com"
    assert "x-session-token" in ok.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in ok.headers  # tokens are headers, no cookies
    bad = await _preflight(cors_client, "https://evil.example.net")
    assert bad.status_code == 400
    assert "access-control-allow-origin" not in bad.headers
    plain = await cors_client.get("/api/health", headers={"Origin": "https://evil.example.net"})
    assert "access-control-allow-origin" not in plain.headers
    good = await cors_client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert good.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_cors_off_without_configured_origins(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/health", headers={"Origin": "https://app.example.com"})
    assert "access-control-allow-origin" not in r.headers


def test_wildcard_cors_origin_is_refused() -> None:
    with pytest.raises(ValueError, match="never"):
        Settings(_env_file=None, cors_origins="*")  # type: ignore[call-arg]


# --- rate limits (all 429 `rate_limited` in the shared shape) -----------------------------------


async def test_session_creation_limited_per_client_by_last_forwarded_hop(
    db_client: httpx.AsyncClient, db_app: FastAPI
) -> None:
    db_app.state.session_rate_limiter = InMemoryRateLimiter(2, timedelta(minutes=1))

    async def create(forwarded: str) -> httpx.Response:
        return await db_client.post("/api/session", headers={"X-Forwarded-For": forwarded})

    assert (await create("6.6.6.6, 10.0.0.1")).status_code == 201
    # A spoofed first hop does not buy a new allowance: the proxy-appended last hop counts.
    assert (await create("7.7.7.7, 10.0.0.1")).status_code == 201
    _assert_error_shape(await create("8.8.8.8, 10.0.0.1"), 429, "rate_limited")
    assert (await create("8.8.8.8, 10.0.0.2")).status_code == 201  # another client


async def test_events_limited_per_session(db_app: FastAPI, db_client: httpx.AsyncClient) -> None:
    db_app.state.events_rate_limiter = InMemoryRateLimiter(2, timedelta(minutes=1))
    tokens = [(await db_client.post("/api/session")).json()["token"] for _ in range(2)]
    body = {"events": [{"name": "quiz_start"}]}

    async def post(token: str) -> httpx.Response:
        return await db_client.post("/api/events", json=body, headers={"X-Session-Token": token})

    assert [(await post(tokens[0])).status_code for _ in range(2)] == [200, 200]
    _assert_error_shape(await post(tokens[0]), 429, "rate_limited")
    assert (await post(tokens[1])).status_code == 200  # the other session is unaffected


async def test_rate_limit_responses_use_error_shape_429(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    from tests.fakes.roleplay import FakeCoach

    db_app.state.coach = FakeCoach()
    await subscribe(pclient)
    run = await start(pclient)
    one = timedelta(minutes=1)
    db_app.state.rate_limiter = InMemoryRateLimiter(1)
    db_app.state.card_rate_limiter = InMemoryRateLimiter(1, one)
    db_app.state.session_rate_limiter = InMemoryRateLimiter(1, one)
    db_app.state.events_rate_limiter = InMemoryRateLimiter(1, one)

    assert (await turn(pclient, run["runId"])).status_code == 200
    _assert_error_shape(await turn(pclient, run["runId"], round_=2), 429, "rate_limited")

    await pclient.get("/api/cards/unknown-card-id-000000")
    _assert_error_shape(await pclient.get("/api/cards/unknown-card-id-000000"), 429, "rate_limited")

    await pclient.post("/api/session")
    _assert_error_shape(await pclient.post("/api/session"), 429, "rate_limited")

    events = {"events": [{"name": "quiz_start"}]}
    await pclient.post("/api/events", json=events)
    _assert_error_shape(await pclient.post("/api/events", json=events), 429, "rate_limited")


def test_idle_rate_limit_keys_are_swept() -> None:
    import asyncio
    from datetime import UTC, datetime

    limiter = InMemoryRateLimiter(5, timedelta(minutes=1))
    start_at = datetime(2026, 1, 5, tzinfo=UTC)

    async def run() -> None:
        for i in range(1023):
            await limiter.allow(f"client-{i}", start_at)
        await limiter.allow("fresh", start_at + timedelta(minutes=5))  # the 1024th call sweeps

    asyncio.run(run())
    assert limiter.tracked_keys == 1


# --- error responses, headers, docs -------------------------------------------------------------


async def test_unhandled_exception_returns_internal_error_shape_and_logs_only_type_and_id(
    app: FastAPI, client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    @app.post("/api/_boom")
    async def boom(payload: dict[str, Any]) -> None:
        raise RuntimeError(f"db password hunter2 and body {payload['note']}")

    caplog.set_level(logging.DEBUG)
    r = await client.post("/api/_boom", json={"note": "BODYSECRET"})
    _assert_error_shape(r, 500, "internal_error")
    request_id = r.headers["x-request-id"]
    assert r.json()["error"]["details"] == {"requestId": request_id}
    assert "hunter2" not in r.text and "Traceback" not in r.text and "RuntimeError" not in r.text
    logs = _logged(caplog)
    assert f"unhandled RuntimeError request_id={request_id}" in logs
    assert "hunter2" not in logs and "BODYSECRET" not in logs and "Traceback" not in logs
    assert all(rec.exc_info is None for rec in caplog.records)
    assert "POST /api/_boom -> 500" in logs


async def test_responses_are_never_cached_and_not_sniffed(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    for r in (
        await pclient.post("/api/session"),
        await pclient.get("/api/quiz"),
        await pclient.get("/api/lessons/m1_l1"),  # 402 error response
        await pclient.get("/api/cards/unknown-card-id-000000"),  # public card
        await pclient.get("/api/health"),
    ):
        assert r.headers["cache-control"] == "no-store", r.url
        assert r.headers["x-content-type-options"] == "nosniff", r.url


async def test_docs_served_by_default_and_hidden_with_docs_enabled_false(
    client: httpx.AsyncClient,
) -> None:
    assert Settings(_env_file=None).docs_enabled is True  # type: ignore[call-arg]
    assert (await client.get("/api/docs")).status_code == 200
    off = create_app(
        Settings(_env_file=None, docs_enabled=False, anthropic_api_key="x")  # type: ignore[call-arg]
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=off), base_url="http://test"
    ) as c:
        assert (await c.get("/api/docs")).status_code == 404
        assert (await c.get("/api/openapi.json")).status_code == 404
