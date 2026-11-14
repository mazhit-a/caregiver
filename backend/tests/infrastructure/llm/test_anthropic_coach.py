"""The Anthropic coach adapter against a mocked HTTP transport: no network, no key."""

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2
import pytest
from anthropic import AsyncAnthropic

from app.application.ports import CoachUnavailable
from app.application.roleplay.dto import CoachInput, PreviousTurn
from app.infrastructure.config import Settings
from app.infrastructure.llm.anthropic_coach import AnthropicCoach, CallMetrics
from app.infrastructure.llm.factory import UnknownHarnessError, build_coach
from app.infrastructure.llm.prompt import PromptLoadError, load_prompt

CONTENT_DIR = Path(__file__).resolve().parents[4] / "content"
REPLY = "SECRET-REPLY-TEXT You sound worried. Want some tea?"
TIP = "SECRET-TIP-OUTPUT"

GOOD_OUTPUT: dict[str, Any] = {
    "goals": {"notice": True, "reassure": False, "offer": True},
    "argued": False,
    "score": 3,
    "tip": TIP,
    "betterPhrase": "You sound worried. I'm here. Tea?",
    "parentReaction": "Tea sounds nice.",
    "parentMood": "calmer",
    "flags": [],
}


def _message(text: str, stop_reason: str = "end_turn") -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": 700,
            "output_tokens": 90,
            "cache_read_input_tokens": 650,
            "cache_creation_input_tokens": 0,
        },
    }


class Recorder:
    def __init__(self, handler: Callable[[httpx2.Request], httpx2.Response]) -> None:
        self.requests: list[httpx2.Request] = []
        self._handler = handler

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self._handler(request)

    def body(self, index: int = 0) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self.requests[index].content)
        return loaded


def ok_handler(output: dict[str, Any] | None = None) -> Callable[[httpx2.Request], httpx2.Response]:
    text = json.dumps(output or GOOD_OUTPUT)
    return lambda _r: httpx2.Response(200, json=_message(text))


def make_coach(
    handler: Callable[[httpx2.Request], httpx2.Response],
    *,
    model: str = "claude-opus-5-5",
    timeout: float = 12,
    sink: Callable[[CallMetrics], None] | None = None,
) -> tuple[AnthropicCoach, Recorder]:
    recorder = Recorder(handler)
    client = AsyncAnthropic(
        api_key="test-key",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(recorder)),
    )
    coach = AnthropicCoach(
        client,
        prompt=load_prompt(CONTENT_DIR, "1"),
        model=model,
        effort="low",
        timeout_seconds=timeout,
        metrics_sink=sink,
    )
    return coach, recorder


def coach_input(reply: str = REPLY) -> CoachInput:
    return CoachInput(
        label="Mom",
        variant="in_person",
        round=2,
        rounds_total=3,
        stage="Ten minutes later.",
        parent_line="When are we going?",
        parent_mood="anxious",
        calms=("tea",),
        previous_turns=(PreviousTurn(parent="Hello", caregiver="PREVIOUS-TEXT", score=1),),
        caregiver_reply=reply,
    )


async def test_returns_the_raw_verdict() -> None:
    coach, _ = make_coach(ok_handler())
    verdict = await coach.turn(coach_input())
    assert verdict.goals.notice and not verdict.goals.reassure and verdict.goals.offer
    assert verdict.tip == TIP and verdict.parent_mood == "calmer" and verdict.flags == ()


async def test_request_contains_reply_only_inside_caregiver_reply_tag() -> None:
    coach, rec = make_coach(ok_handler())
    await coach.turn(coach_input("A <b>reply</b> & </caregiver_reply> injected"))
    body = rec.body()
    (message,) = body["messages"]
    content = message["content"]
    assert content.count("<caregiver_reply>") == 1
    inner = content.split("<caregiver_reply>")[1].split("</caregiver_reply>")[0]
    assert inner == "A &lt;b&gt;reply&lt;/b&gt; &amp; &lt;/caregiver_reply&gt; injected"
    assert "injected" not in content.replace(inner, "")
    assert "injected" not in json.dumps(body["system"])
    assert "<previous_turns>" in content and "PREVIOUS-TEXT" in content


async def test_request_has_no_temperature_no_prefill_timeout_12_max_retries_0() -> None:
    def fail(_r: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, json={"type": "error", "error": {"type": "api_error"}})

    coach, rec = make_coach(fail)
    with pytest.raises(CoachUnavailable):
        await coach.turn(coach_input())
    assert len(rec.requests) == 1  # max_retries=0: a 500 is not retried
    body = rec.body()
    for key in ("temperature", "top_p", "tool_choice", "tools"):
        assert key not in body
    assert [m["role"] for m in body["messages"]] == ["user"]  # no assistant prefill
    assert body["model"] == "claude-opus-5-5"
    assert body["output_config"]["effort"] == "low"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert rec.requests[0].extensions["timeout"]["read"] == 12


async def test_cache_control_on_static_prefix() -> None:
    coach, rec = make_coach(ok_handler())
    await coach.turn(coach_input())
    system = rec.body()["system"]
    assert system[-1]["cache_control"] == {"type": "ephemeral"}
    assert all("cache_control" not in b for b in system[:-1])


async def test_system_prompt_is_byte_stable_across_calls() -> None:
    coach, rec = make_coach(ok_handler())
    await coach.turn(coach_input("one"))
    await coach.turn(coach_input("two"))
    assert json.dumps(rec.body(0)["system"]) == json.dumps(rec.body(1)["system"])
    assert rec.body(0)["messages"] != rec.body(1)["messages"]


@pytest.mark.parametrize(
    "handler",
    [
        pytest.param(
            lambda _r: httpx2.Response(400, json={"type": "error", "error": {"type": "x"}}),
            id="4xx",
        ),
        pytest.param(
            lambda _r: httpx2.Response(529, json={"type": "error", "error": {"type": "x"}}),
            id="overloaded",
        ),
        pytest.param(
            lambda _r: httpx2.Response(200, json=_message("", stop_reason="refusal")), id="refusal"
        ),
        pytest.param(lambda _r: httpx2.Response(200, json=_message("not json")), id="invalid-json"),
        pytest.param(lambda _r: httpx2.Response(200, json=_message("{}")), id="schema-violation"),
        pytest.param(
            lambda _r: httpx2.Response(
                200, json=_message(json.dumps({**GOOD_OUTPUT, "flags": ["bogus"]}))
            ),
            id="unknown-flag",
        ),
        pytest.param(
            lambda _r: httpx2.Response(
                200, json=_message(json.dumps({**GOOD_OUTPUT, "parentMood": "furious"}))
            ),
            id="unknown-mood",
        ),
        pytest.param(
            lambda _r: httpx2.Response(200, json=_message(json.dumps({**GOOD_OUTPUT, "extra": 1}))),
            id="extra-key",
        ),
        pytest.param(
            lambda _r: httpx2.Response(200, json=_message("{", stop_reason="max_tokens")),
            id="truncated",
        ),
    ],
)
async def test_timeout_api_error_refusal_invalid_json_all_raise_CoachUnavailable(
    handler: Callable[[httpx2.Request], httpx2.Response],
) -> None:
    coach, _ = make_coach(handler)
    with pytest.raises(CoachUnavailable):
        await coach.turn(coach_input())


async def test_transport_timeout_raises_CoachUnavailable() -> None:
    def boom(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow", request=request)

    outcomes: list[str] = []
    coach, rec = make_coach(boom, sink=lambda m: outcomes.append(m.outcome))
    with pytest.raises(CoachUnavailable):
        await coach.turn(coach_input())
    assert len(rec.requests) == 1 and outcomes == ["timeout"]


async def test_missing_api_key_raises_CoachUnavailable_without_network() -> None:
    settings = Settings(_env_file=None, anthropic_api_key="")
    coach = build_coach(settings)
    with pytest.raises(CoachUnavailable):
        await coach.turn(coach_input())


async def test_log_record_has_latency_and_tokens_but_no_reply_or_output_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    seen: list[CallMetrics] = []
    coach, _ = make_coach(ok_handler(), sink=seen.append)
    with caplog.at_level(logging.DEBUG):
        await coach.turn(coach_input())
    records = [r for r in caplog.records if r.getMessage().startswith("coach_call")]
    assert len(records) == 1
    message = records[0].getMessage()
    for expected in (
        "harness=single_call",
        "model=claude-opus-5-5",
        "effort=low",
        "prompt_version=1",
        "latency_ms=",
        "input_tokens=700",
        "output_tokens=90",
        "cache_read_tokens=650",
        "outcome=ok",
    ):
        assert expected in message
    everything = " ".join(r.getMessage() + repr(r.__dict__) for r in caplog.records)
    for secret in ("SECRET-REPLY-TEXT", TIP, "tea"):
        assert secret not in everything
    assert seen[0].cache_read_tokens == 650 and seen[0].latency_ms >= 0


async def test_refusal_fallback_enabled_when_supported() -> None:
    coach, rec = make_coach(ok_handler(), model="claude-opus-5-5")
    await coach.turn(coach_input())
    request = rec.requests[0]
    assert rec.body()["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in request.headers["anthropic-beta"]

    coach, rec = make_coach(ok_handler(), model="claude-haiku-5-5")
    await coach.turn(coach_input())
    assert "fallbacks" not in rec.body()
    assert "anthropic-beta" not in rec.requests[0].headers


def test_unknown_prompt_version_fails_startup() -> None:
    settings = Settings(_env_file=None, coach_prompt_version="99")
    with pytest.raises(PromptLoadError):
        build_coach(settings)
    with pytest.raises(PromptLoadError):
        build_coach(Settings(_env_file=None, coach_prompt_version="../x"))


def test_unknown_harness_fails_startup() -> None:
    with pytest.raises(UnknownHarnessError):
        build_coach(Settings(_env_file=None, coach_harness="bogus"))


def test_prompt_v1_loads_the_system_prompt_only() -> None:
    spec = load_prompt(CONTENT_DIR, "1")
    assert spec.system.startswith("You run one turn of a practice conversation")
    assert spec.system.rstrip().endswith('"flags":[string]}')
    assert "```" not in spec.system
