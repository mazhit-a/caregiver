"""Eval wiring follow-up: parallel_split through the registry, per-call aggregation, cache
fingerprints, parent-model presets, the dry-run estimate per stage and the --judge flag.
All offline: fake SDK clients, no key, no network."""

import asyncio
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.infrastructure.config import Settings
from app.infrastructure.llm.anthropic_coach import CallMetrics
from app.infrastructure.llm.parallel_split import ParallelSplitCoach
from app.infrastructure.llm.prompt import PromptLoadError
from app.infrastructure.llm.schema import CoachAnalysisResponse, CoachResponse, ParentResponse
from evals.cache import ResultCache, config_fingerprint, fingerprint_parts
from evals.client import CoachConfig, build_eval_coach, production_config
from evals.configs import STAGES, candidate
from evals.cost import estimate_config, estimate_run, format_estimate, table_token_estimate
from evals.dataset import Split, load_split
from evals.graders.judge import JudgeResponse
from evals.metrics import compute_metrics, load_prices
from evals.run import EXIT_JUDGE_BLOCKED, main
from evals.runner import CallRecorder, EvalContext, aggregate_calls, run_measured
from tests.evals.calibrate_helpers import passing_calibration
from tests.evals.conftest import CONTENT_DIR, make_call, make_case
from tests.evals.judge_fakes import judge_response
from tests.evals.test_runner import GOOD

PRICES = load_prices()
V1 = CoachConfig(name="c", model="claude-opus-5-5", effort="low", prompt_version="1")
SPLIT = CoachConfig(
    name="s",
    model="claude-opus-5-5",
    effort="low",
    prompt_version="2",
    harness="parallel_split",
    parent_model="claude-haiku-5-5",
)


def _settings(**kw: Any) -> Settings:
    return Settings(anthropic_api_key="", content_dir=CONTENT_DIR, **kw)


class RoutingClient:
    """One fake SDK client for coach (single and split) and judge calls, routed by schema."""

    def __init__(self, *, coach_usage: tuple[int, int] = (100, 50)) -> None:
        self.requests: list[dict[str, Any]] = []
        self.coach_usage = coach_usage
        self.messages = SimpleNamespace(parse=self._parse)
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def with_options(self, *, max_retries: int, timeout: float) -> "RoutingClient":
        return self

    async def _parse(self, **kw: Any) -> Any:
        self.requests.append(kw)
        schema = kw["output_format"]
        parsed: Any
        if schema is CoachResponse:
            parsed = GOOD
        elif schema is CoachAnalysisResponse:
            parsed = CoachAnalysisResponse.model_validate(
                {
                    "goals": {"notice": True, "reassure": True, "offer": True},
                    "argued": False,
                    "score": 3,
                    "tip": GOOD.tip,
                    "betterPhrase": GOOD.better_phrase,
                    "flags": [],
                }
            )
        elif schema is ParentResponse:
            parsed = ParentResponse.model_validate(
                {"parentReaction": "Tea sounds nice.", "parentMood": "calmer"}
            )
        elif schema is JudgeResponse:
            parsed = judge_response(5, 4, 3)
        else:  # pragma: no cover
            raise AssertionError(schema)
        if schema is JudgeResponse:
            tokens = (300, 60)
        elif schema is ParentResponse:
            tokens = (self.coach_usage[0] // 2, 10)
        else:
            tokens = self.coach_usage
        usage = SimpleNamespace(
            input_tokens=tokens[0],
            output_tokens=tokens[1],
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        await asyncio.sleep(0)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=parsed, usage=usage)


# ------------------------------------------------------------------ (1) harness wiring


def test_build_eval_coach_builds_parallel_split_with_the_parent_model() -> None:
    coach = build_eval_coach(SPLIT, _settings(), RoutingClient())
    assert isinstance(coach, ParallelSplitCoach)
    assert coach.parent_model == "claude-haiku-5-5"


def test_parallel_split_needs_a_prompt_with_call_sections() -> None:
    v1_split = CoachConfig(
        name="x", model="m", effort="low", prompt_version="1", harness="parallel_split"
    )
    with pytest.raises(PromptLoadError):
        build_eval_coach(v1_split, _settings(), None)


def test_production_config_carries_the_parent_model_from_settings() -> None:
    assert production_config(_settings()).parent_model is None
    cfg = production_config(_settings(coach_parent_model="claude-haiku-5-5"))
    assert cfg.parent_model == "claude-haiku-5-5"


def test_presets_can_set_a_cheaper_parent_model() -> None:
    c = candidate("opus-low+parallel_split:haiku", "2")
    assert (c.harness, c.model, c.parent_model) == (
        "parallel_split",
        "claude-opus-5-5",
        "claude-haiku-5-5",
    )
    assert c.name == "opus-low-v2-parallel_split-parent-haiku"
    assert candidate("opus-low+parallel_split", "2").parent_model is None
    for bad in ("opus-low+parallel_split:gpt", "opus-low+single_call:haiku"):
        with pytest.raises(KeyError):
            candidate(bad, "2")


# ------------------------------------------------------------------ (2) fingerprints


def test_v1_fingerprint_is_byte_identical_to_before() -> None:
    # Pinned from the code before this change (the note hash is written for v1 only).
    parts = fingerprint_parts(V1, CONTENT_DIR)
    assert parts == {
        "model": "claude-opus-5-5",
        "effort": "low",
        "thinking": None,
        "harness": "single_call",
        "promptVersion": "1",
        "promptFileSha256": "cf67b1893e18a76be10f4ee9dfddfbcb8d7dfdf88390b43465e810ae8559e55c",
        "inputFormatNoteSha256": "d9ced245c0826c33e937b3916eacd4b52b20f7eabd0b6e87b82ca001f310e7d4",
    }
    assert (
        config_fingerprint(V1, CONTENT_DIR)
        == "ed36d2cb56a14f182e535d49d1bc6d26e122ee92e97d6571a56cf0f50e955d82"
    )


def test_note_hash_only_for_versions_that_use_it_and_parent_model_only_when_set() -> None:
    v2 = CoachConfig(name="c", model="claude-opus-5-5", effort="low", prompt_version="2")
    assert "inputFormatNoteSha256" not in fingerprint_parts(v2, CONTENT_DIR)
    assert "parentModel" not in fingerprint_parts(v2, CONTENT_DIR)
    assert fingerprint_parts(SPLIT, CONTENT_DIR)["parentModel"] == "claude-haiku-5-5"
    other = CoachConfig(**{**SPLIT.__dict__, "parent_model": "claude-sonnet-5-5"})
    assert config_fingerprint(SPLIT, CONTENT_DIR) != config_fingerprint(other, CONTENT_DIR)


# ------------------------------------------------------------------ (3) runner metrics


def _calls() -> tuple[CallMetrics, CallMetrics]:
    coach = make_call(model="claude-opus-5-5", input_tokens=2000, output_tokens=300, cache_read=500)
    parent = make_call(model="claude-haiku-5-5", input_tokens=1500, output_tokens=100)
    from dataclasses import replace

    return replace(coach, role="coach", latency_ms=900.0), replace(
        parent, role="parent", latency_ms=400.0, outcome="refusal"
    )


def test_aggregate_calls_sums_usage_takes_wall_time_and_worst_outcome() -> None:
    coach, parent = _calls()
    one = aggregate_calls([coach], 950.0)
    assert one is coach  # single_call behaviour is unchanged
    assert aggregate_calls([], 1.0) is None
    both = aggregate_calls([parent, coach], 950.0)  # order does not matter
    assert both is not None
    assert (both.input_tokens, both.output_tokens, both.cache_read_tokens) == (3500, 400, 500)
    assert both.latency_ms == 950.0  # the case wall time, not 900 + 400
    assert both.outcome == "refusal"
    assert both.model == "claude-opus-5-5" and both.role == "merged"


async def test_parallel_split_case_is_priced_as_the_sum_of_both_calls(ctx: EvalContext) -> None:
    client = RoutingClient(coach_usage=(2000, 300))
    recorder = CallRecorder()
    coach = build_eval_coach(
        SPLIT,
        _settings(),
        client,
        metrics_sink=recorder.sink,
    )
    measured = await run_measured(coach, [make_case()], ctx, recorder=recorder)
    m = measured[0]
    assert len(m.calls) == 2 and [c.role for c in m.calls] == ["coach", "parent"]
    assert m.call is not None and m.call.input_tokens == 2000 + 1000
    assert m.call.output_tokens == 310
    metrics = compute_metrics(SPLIT, measured, PRICES)
    assert metrics.cost is not None
    expected = (
        (2000 * 4.0 + 300 * 20.0)  # coach on opus
        + (1000 * 0.10 + 10 * 0.50)  # parent on haiku
    ) / 1e6
    assert metrics.cost.per_turn_usd == pytest.approx(expected)
    assert metrics.cost.per_lesson_usd == pytest.approx(expected * 3)
    assert metrics.latency.p50_ms == m.wall_ms  # wall time, not a sum of call latencies


async def test_single_call_measured_is_unchanged(ctx: EvalContext) -> None:
    client = RoutingClient()
    recorder = CallRecorder()
    coach = build_eval_coach(V1, _settings(), client, metrics_sink=recorder.sink)
    (m,) = await run_measured(coach, [make_case()], ctx, recorder=recorder)
    assert m.calls == () and m.call is not None and m.call.role == "single"
    assert len(m.usage_calls) == 1


async def test_cache_keeps_both_calls_and_a_hit_prices_the_same(
    ctx: EvalContext, tmp_path: Path
) -> None:
    cache = ResultCache(tmp_path / "cache")
    fp = config_fingerprint(SPLIT, CONTENT_DIR)
    client = RoutingClient()
    recorder = CallRecorder()
    coach = build_eval_coach(SPLIT, _settings(), client, metrics_sink=recorder.sink)
    first = await run_measured(
        coach, [make_case()], ctx, recorder=recorder, cache=cache, fingerprint=fp
    )
    n = len(client.requests)
    again = await run_measured(
        coach, [make_case()], ctx, recorder=recorder, cache=cache, fingerprint=fp
    )
    assert len(client.requests) == n and again[0].cached
    assert again[0].calls == first[0].calls and len(again[0].calls) == 2
    a = compute_metrics(SPLIT, first, PRICES).cost
    b = compute_metrics(SPLIT, again, PRICES).cost
    assert a is not None and b is not None and a.per_turn_usd == b.per_turn_usd


async def test_one_failed_call_gives_the_worst_outcome(ctx: EvalContext) -> None:
    class Failing(RoutingClient):
        async def _parse(self, **kw: Any) -> Any:
            if kw["output_format"] is ParentResponse:
                raise RuntimeError("boom")
            return await super()._parse(**kw)

    client = Failing()
    recorder = CallRecorder()
    coach = build_eval_coach(SPLIT, _settings(), client, metrics_sink=recorder.sink)
    (m,) = await run_measured(coach, [make_case()], ctx, recorder=recorder)
    assert m.result.outcome is None and m.call is not None
    parent = next(c for c in m.calls if c.role == "parent")
    assert parent.outcome not in ("ok", "cancelled")
    assert m.call.outcome == parent.outcome  # the real failure, not the cancelled/ok sibling


# ------------------------------------------------------------------ cost estimate


def test_parallel_split_estimate_is_two_calls_per_turn_with_each_models_price() -> None:
    tokens = table_token_estimate(SPLIT, [make_case()], CONTENT_DIR)
    assert tokens.parent is not None
    assert tokens.parent.output_tokens == tokens.output_tokens // 2
    est = estimate_config(SPLIT, 10, tokens, PRICES)
    assert est.calls == 20 and est.turns == 10 and est.parent_model == "claude-haiku-5-5"
    coach = (tokens.input_tokens * 4.0 + tokens.output_tokens * 20.0) * 10 / 1e6
    parent = (tokens.parent.input_tokens * 0.10 + tokens.parent.output_tokens * 0.50) * 10 / 1e6
    assert est.usd == pytest.approx(coach + parent)
    assert "10 turns x 2 calls" in format_estimate(
        estimate_run([(SPLIT, 10, tokens)], PRICES), 1, 10
    )
    plain = estimate_config(V1, 10, table_token_estimate(V1, [make_case()], CONTENT_DIR), PRICES)
    assert plain.calls == 10 and plain.parent_model is None


def test_split_estimate_is_cheaper_with_a_cheaper_parent_model() -> None:
    same = CoachConfig(**{**SPLIT.__dict__, "parent_model": None})
    t = table_token_estimate(SPLIT, [make_case()], CONTENT_DIR)
    assert estimate_config(SPLIT, 5, t, PRICES).usd < estimate_config(same, 5, t, PRICES).usd


def test_parallel_split_estimate_rejects_a_prompt_without_call_sections() -> None:
    v1 = CoachConfig(
        name="x", model="m", effort="low", prompt_version="1", harness="parallel_split"
    )
    with pytest.raises(PromptLoadError):
        table_token_estimate(v1, [make_case()], CONTENT_DIR)


# ------------------------------------------------------------------ (5) offline CLI / dry runs


def _dry(argv: list[str], capsys: pytest.CaptureFixture[str], tmp_path: Path) -> tuple[int, str]:
    code = main(
        [*argv, "--dry-run", "--cache-dir", str(tmp_path / "c")],
        settings=_settings(),
        client_factory=lambda _s: pytest.fail("no client may be built in a dry run"),
    )
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def test_dry_run_harness_stage_prints_single_call_and_parallel_split_estimates(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    code, out = _dry(["--stage", "harness", "--prompt-version", "2"], capsys, tmp_path)
    assert code == 0 and "Dry run" in out
    lines = {ln.split()[0]: ln for ln in out.splitlines() if ln.startswith("  opus")}
    assert set(lines) == {"opus-low-v2", "opus-low-v2-parallel_split"}
    assert "96 calls" in lines["opus-low-v2"]
    assert "96 turns x 2 calls (192 calls)" in lines["opus-low-v2-parallel_split"]
    assert "TOTAL 288 calls" in out  # 96 single + 2 x 96 split


def test_dry_run_prompt_stage_prints_both_versions(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    code, out = _dry(["--stage", "prompt"], capsys, tmp_path)
    assert code == 0 and "opus-low-v1" in out and "opus-low-v2" in out
    assert "TOTAL 192 calls" in out


def test_dry_run_with_a_cheaper_parent_preset(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    argv = ["--prompt-version", "2", "--config", "opus-low+parallel_split:haiku"]
    code, out = _dry(argv, capsys, tmp_path)
    assert code == 0 and "parent claude-haiku-5-5" in out


def test_dry_run_split_on_prompt_v1_is_a_configuration_error(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    code, out = _dry(["--stage", "harness", "--prompt-version", "1"], capsys, tmp_path)
    assert code == 1
    assert "no coach/parent call sections" in out


def test_stage_presets_are_unchanged() -> None:
    assert STAGES["harness"] == ("opus-low+single_call", "opus-low+parallel_split")


# ------------------------------------------------------------------ (4) --judge


def _judge_args(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "--set",
        "test",
        "--runs",
        "1",
        "--stage",
        "judged",
        "--cache-dir",
        str(tmp_path / "cache"),
        "--report-dir",
        str(tmp_path / "rep"),
        "--calibration-dir",
        str(tmp_path / "calib"),
        "--judge",
        *extra,
    ]


def _run(argv: list[str], client: RoutingClient, **kw: Any) -> int:
    return main(
        argv,
        settings=_settings(),
        client_factory=lambda _s: client,
        today=date(2026, 11, 14),
        interactive=False,
        **kw,
    )


def test_judge_without_calibration_stops_before_any_call_with_exit_3(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client = RoutingClient()
    built: list[int] = []

    def factory(_s: Settings) -> RoutingClient:
        built.append(1)
        return client

    code = main(
        _judge_args(tmp_path, "--yes", "--max-cost-usd", "5"),
        settings=_settings(),
        client_factory=factory,
        interactive=False,
    )
    err = capsys.readouterr().err
    assert code == EXIT_JUDGE_BLOCKED == 3
    assert "calibration" in err and "No model call was made" in err
    assert client.requests == [] and built == []
    assert not (tmp_path / "rep").exists()


def test_judge_dry_run_includes_the_judge_in_one_estimate_and_warns_when_uncalibrated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        [
            *("--set", "test", "--runs", "1", "--judge", "--dry-run"),
            *("--cache-dir", str(tmp_path / "c")),
            *("--calibration-dir", str(tmp_path / "calib")),
        ],
        settings=_settings(),
        client_factory=lambda _s: pytest.fail("no client may be built in a dry run"),
    )
    captured = capsys.readouterr()
    n = len(load_split(Split.TEST))
    assert code == 0
    assert f"TOTAL {2 * n} calls" in captured.out  # n coach + n judge calls, one estimate
    assert "  judge " in captured.out
    assert "would stop (exit 3)" in captured.err


def test_judged_run_adds_quality_to_metrics_and_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    passing_calibration(tmp_path / "calib")
    client = RoutingClient()
    # the combined estimate must be below the cap, and one cap covers coach + judge
    assert _run(_judge_args(tmp_path, "--yes", "--max-cost-usd", "5"), client) == 1  # no winner
    schemas = [r["output_format"] for r in client.requests]
    assert schemas.count(JudgeResponse) > 0 and schemas.count(CoachResponse) > 0
    report = json.loads((tmp_path / "rep" / "2026-11-14-judged.json").read_text(encoding="utf-8"))
    cfg = report["configs"][0]
    assert cfg["metrics"]["quality"] == pytest.approx((1.0 + 0.75 + 0.5) / 3)
    assert cfg["judge"]["judged"] > 0 and "reasons" not in cfg["judge"]
    md = (tmp_path / "rep" / "2026-11-14-judged.md").read_text(encoding="utf-8")
    assert "## Judged quality" in md and "quality 75.0%" in md
    assert "quality 0.3000" in md  # the quality weight is used, not renormalised away


def test_judge_cap_applies_to_the_combined_total(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    passing_calibration(tmp_path / "calib")
    client = RoutingClient()
    code = _run(_judge_args(tmp_path, "--yes", "--max-cost-usd", "0.0000001"), client)
    assert code == 2 and client.requests == []
    assert "exceeds --max-cost-usd" in capsys.readouterr().err


def test_without_judge_quality_stays_absent(tmp_path: Path) -> None:
    client = RoutingClient()
    argv = [a for a in _judge_args(tmp_path, "--yes", "--max-cost-usd", "5") if a != "--judge"]
    _run(argv, client)
    assert all(r["output_format"] is not JudgeResponse for r in client.requests)
    report = json.loads((tmp_path / "rep" / "2026-11-14-judged.json").read_text(encoding="utf-8"))
    assert report["configs"][0]["metrics"]["quality"] is None
    assert report["configs"][0]["judge"] is None
