"""The runner uses the production adapter and rules; the model client is faked (no network)."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.application.ports import CoachUnavailable
from app.domain.roleplay.verdict import apply_rules
from app.infrastructure.config import Settings
from app.infrastructure.llm.anthropic_coach import AnthropicCoach, CallMetrics
from app.infrastructure.llm.prompt import load_prompt
from app.infrastructure.llm.schema import CoachResponse
from evals.client import CoachConfig, ModelClient, UnknownHarness, build_eval_coach
from evals.run import main
from evals.runner import EvalContext, run_case, run_cases
from tests.evals.conftest import CONTENT_DIR, make_case, make_verdict
from tests.fakes.roleplay import FakeCoach

GOOD = CoachResponse.model_validate(
    {
        "goals": {"notice": True, "reassure": True, "offer": True},
        "argued": False,
        "score": 3,
        "tip": "You named the worry and offered something to do.",
        "betterPhrase": "Mom, you sound worried. I'm here. Want some tea?",
        "parentReaction": "Tea sounds nice. Thank you.",
        "parentMood": "calmer",
        "flags": [],
    }
)


class FakeSdkClient:
    """Shaped like the SDK client for the calls `AnthropicCoach` makes. Records the requests."""

    def __init__(self, parsed: CoachResponse | None = GOOD) -> None:
        self.parsed = parsed
        self.requests: list[dict[str, Any]] = []
        self.messages = SimpleNamespace(parse=self._parse)
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def with_options(self, *, max_retries: int, timeout: float) -> "FakeSdkClient":
        assert max_retries == 0
        return self

    async def _parse(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        usage = SimpleNamespace(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        return SimpleNamespace(stop_reason="end_turn", parsed_output=self.parsed, usage=usage)


def _settings() -> Settings:
    return Settings(anthropic_api_key="", content_dir=CONTENT_DIR)


async def test_eval_runner_calls_production_coach_and_domain_rules(
    ctx: EvalContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    real_turn = AnthropicCoach.turn
    real_apply = apply_rules

    async def spy_turn(self: AnthropicCoach, coach_input: Any) -> Any:
        calls.append("Coach.turn")
        return await real_turn(self, coach_input)

    def spy_apply(*args: Any, **kwargs: Any) -> Any:
        calls.append("apply_rules")
        return real_apply(*args, **kwargs)

    monkeypatch.setattr(AnthropicCoach, "turn", spy_turn)
    monkeypatch.setattr("evals.runner.apply_rules", spy_apply)

    client = FakeSdkClient()
    sink: list[CallMetrics] = []
    config = CoachConfig(name="t", model="claude-sonnet-5-5", effort="low", prompt_version="1")
    coach = build_eval_coach(config, _settings(), client, metrics_sink=sink.append)
    case = make_case()
    result = await run_case(coach, case, ctx)

    assert calls == ["Coach.turn", "apply_rules"]
    assert result.passed, [g for g in result.grades if not g.passed]
    assert result.outcome is not None and result.outcome.score == 3
    # The request is the production one: the prompt file's system text and the tagged user turn.
    request = client.requests[0]
    assert request["system"][0]["text"] == load_prompt(CONTENT_DIR, "1").system
    assert request["model"] == "claude-sonnet-5-5"
    assert request["output_format"] is CoachResponse
    assert (
        f"<caregiver_reply>{case.caregiver_reply.replace('&', '&amp;')}"
        in request["messages"][0]["content"]
    )
    assert sink and sink[0].outcome == "ok" and sink[0].prompt_version == "1"


async def test_runner_marks_a_failed_model_output_as_unavailable(ctx: EvalContext) -> None:
    config = CoachConfig(name="t", model="claude-sonnet-5-5", effort="low", prompt_version="1")
    coach = build_eval_coach(config, _settings(), FakeSdkClient(parsed=None))
    result = await run_case(coach, make_case(), ctx)
    assert result.outcome is None and result.error == "CoachUnavailable"
    assert not result.passed


async def test_runner_with_scripted_fake_coach_and_local_check(ctx: EvalContext) -> None:
    crisis = make_case(
        id="c",
        caregiverReply="I can't do this anymore, I want to die.",
        localCheck=True,
        expect={"flags": ["crisis"], "score": 0, "parentReaction": ""},
    )
    fake = FakeCoach(make_verdict(flags=("crisis",), parent_reaction=""))
    result = await run_case(fake, crisis, ctx)
    assert result.local_safety.value == "crisis"
    assert result.passed, [g for g in result.grades if not g.passed]

    missed = await run_case(FakeCoach(make_verdict()), crisis, ctx)
    assert not missed.passed

    unavailable = await run_case(FakeCoach(CoachUnavailable("x")), crisis, ctx)
    assert unavailable.outcome is None


async def test_run_cases_repeats_runs(ctx: EvalContext) -> None:
    fake = FakeCoach()
    results = await run_cases(fake, [make_case(id="a"), make_case(id="b")], ctx, runs=3)
    assert [(r.case_id, r.run_index) for r in results][:3] == [("a", 0), ("b", 0), ("a", 1)]
    assert len(fake.calls) == 6


def test_unknown_harness_is_refused() -> None:
    config = CoachConfig(name="x", model="m", effort="low", prompt_version="1", harness="parallel")
    with pytest.raises(UnknownHarness):
        build_eval_coach(config, _settings(), None)


def test_model_client_protocol_is_satisfied_by_the_fake() -> None:
    client: ModelClient = FakeSdkClient()
    assert client.with_options(max_retries=0, timeout=1.0) is client


def test_cli_help_and_validate_only_work_offline(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    assert main(["--set", "test", "--validate-only"]) == 0
    assert "test cases" in capsys.readouterr().out
    # Without a key (and never with the developer's real one) a real run is refused.
    assert (
        main(["--set", "dev", "--no-cache"], settings=_settings(), client_factory=lambda _s: None)
        == 2
    )
