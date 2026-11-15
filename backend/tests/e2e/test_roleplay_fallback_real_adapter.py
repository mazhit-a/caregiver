"""SLOW end-to-end tests: the role-play falls back within the 12 s deadline through the REAL
Anthropic adapter (not the FakeCoach). They measure the real wall clock (`time.monotonic`, no
sleeps), so they carry `@pytest.mark.slow` (approved exception in `.claude/rules/tests.md`): the
default run skips them (`-m "not slow"`), the acceptance run is `uv run pytest -m slow`.

Case 1: no `ANTHROPIC_API_KEY` (the adapter has no client; every turn falls back at once).
Case 2: a key is set and the HTTP layer hangs (a mock transport awaiting an Event that is never
set, through the SDK's `http_client` seam); the 12 s deadline must trigger the fallback.
No network is used in either case.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
import httpx2
import pytest
from anthropic import AsyncAnthropic
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.config import Settings
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.llm.anthropic_coach import AnthropicCoach
from app.infrastructure.llm.factory import make_coach
from app.infrastructure.llm.prompt import load_prompt
from app.main import create_app
from tests.e2e.journey import answer, answer_quiz_persona_b, ok
from tests.fakes.clock import FixedClock
from tests.lesson_content import REPO

pytestmark = pytest.mark.slow

WALL_CLOCK_BUDGET_SECONDS = 13.0


def _settings(database_url: str, api_key: str) -> Settings:
    return Settings(
        _env_file=None,
        database_url=database_url,
        stripe_secret_key="sk_test_dummy",
        anthropic_api_key=api_key,
    )


async def _app(database_url: str, api_key: str) -> FastAPI:
    app = create_app(_settings(database_url, api_key))
    app.state.clock = FixedClock()
    app.state.content = JsonContentProvider.from_directory(REPO / "content")
    return app


@pytest.fixture
async def no_key_app(
    test_database_url: str, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[FastAPI]:
    app = await _app(test_database_url, "")
    yield app
    await app.state.engine.dispose()


@pytest.fixture
async def hanging_http_app(
    test_database_url: str, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[FastAPI]:
    """A key is set; the Anthropic SDK's HTTP layer never answers (not set, never released)."""
    never = asyncio.Event()

    async def hang(request: httpx2.Request) -> httpx2.Response:
        app.state.http_requests += 1
        await never.wait()
        raise AssertionError("unreachable: the event is never set")

    settings = _settings(test_database_url, "sk-ant-test-not-real")
    app = await _app(test_database_url, "sk-ant-test-not-real")
    app.state.http_requests = 0
    client = AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        max_retries=0,
        timeout=settings.llm_timeout_seconds,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(hang)),
    )
    app.state.coach = make_coach(
        settings.coach_harness,
        client,
        prompt=load_prompt(settings.content_dir, settings.coach_prompt_version),
        model=settings.coach_model,
        parent_model=settings.coach_parent_model or None,
        effort=settings.coach_effort,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    yield app
    await app.state.engine.dispose()


async def _lesson_with_roleplay_falling_back(app: FastAPI) -> float:
    """Quiz, demo subscription, lesson 1 role-play (3 turns) and completion; returns the seconds
    the first (slowest) turn took."""
    assert app.state.settings.llm_timeout_seconds == 12  # the default deadline
    assert isinstance(app.state.coach, AnthropicCoach)  # the real adapter, not a fake
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["X-Session-Token"] = (await ok(await client.post("/api/session"), 201))[
            "token"
        ]
        await answer_quiz_persona_b(client)
        await ok(await client.post("/api/billing/demo", json={"autoRenewConsent": True}))
        await answer(client, "m1_l1", "setup", "phone")
        run = await ok(
            await client.post(
                "/api/roleplay/start", json={"lessonId": "m1_l1", "context": "lesson"}
            )
        )
        slowest = 0.0
        for number in range(1, run["roundsTotal"] + 1):
            started = time.monotonic()
            turn: dict[str, Any] = await ok(
                await client.post(
                    f"/api/roleplay/{run['runId']}/turn",
                    json={"round": number, "reply": "You sound worried. I'm here. Tea?"},
                )
            )
            elapsed = time.monotonic() - started
            slowest = max(slowest, elapsed)
            assert turn["mode"] == "fallback" and turn["coach"] is None
            assert turn["fallbackScenarios"]  # the lesson's own multiple-choice scenarios take over
            assert elapsed <= WALL_CLOCK_BUDGET_SECONDS, (number, elapsed)
        finished = await ok(
            await client.post(f"/api/roleplay/{run['runId']}/finish", json={"phrases": []})
        )
        assert finished["scores"] == []
        done = await ok(await client.post("/api/lessons/m1_l1/complete"))
        assert done["lessonId"] == "m1_l1" and done["doneAt"]
    return slowest


async def test_roleplay_fallback_within_13_seconds_when_no_api_key_and_lesson_completes(
    no_key_app: FastAPI,
) -> None:
    slowest = await _lesson_with_roleplay_falling_back(no_key_app)
    assert slowest < 1  # no HTTP call is attempted at all


async def test_roleplay_fallback_within_13_seconds_when_http_hangs_and_lesson_completes(
    hanging_http_app: FastAPI,
) -> None:
    started = time.monotonic()
    slowest = await _lesson_with_roleplay_falling_back(hanging_http_app)
    total = time.monotonic() - started
    assert hanging_http_app.state.http_requests == 1  # the request really went out and hung
    assert 11 <= slowest <= WALL_CLOCK_BUDGET_SECONDS  # the deadline, not an instant failure
    assert total <= WALL_CLOCK_BUDGET_SECONDS + 2  # turns 2 and 3 fall back at once (run stays so)
