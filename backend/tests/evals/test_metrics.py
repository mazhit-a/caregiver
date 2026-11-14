"""Metrics from fake outputs and fake usage. No model, no network."""

import asyncio
from pathlib import Path

import pytest

from app.application.roleplay.dto import CoachInput
from app.domain.roleplay.verdict import CoachVerdict, Goals
from evals.client import CoachConfig
from evals.metrics import (
    PriceError,
    compute_metrics,
    consistency,
    load_prices,
    percentile,
)
from evals.runner import CallRecorder, EvalContext, run_measured
from tests.evals.conftest import make_call, make_case, make_measured, make_verdict

CONFIG = CoachConfig(name="c", model="claude-opus-5-5", effort="low", prompt_version="1")
PRICES = load_prices()


def test_price_table_records_retrieval_date_and_has_the_three_models() -> None:
    assert PRICES.retrieved_on == "2026-11-14"
    assert "re-check" in PRICES.note.lower()
    assert PRICES.price("claude-opus-5-5").input_per_mtok == 4.0
    assert PRICES.price("claude-opus-5-5").output_per_mtok == 20.0
    assert PRICES.price("claude-opus-5-5").cache_read_per_mtok == 0.20
    assert PRICES.price("claude-sonnet-5-5").cache_read_per_mtok == 0.10
    assert PRICES.price("claude-haiku-5-5").output_per_mtok == 0.50
    with pytest.raises(PriceError):
        PRICES.price("claude-unknown")


def test_accuracy_per_goal_exact_score_argued_and_flag_precision_recall(
    ctx: EvalContext,
) -> None:
    exp = {"goals": {"notice": True, "reassure": True, "offer": True}, "argued": False, "score": 3}
    a = make_case(id="a", expect=exp)
    b = make_case(id="b", expect={**exp, "score": 2, "goals": {"notice": True, "reassure": False}})
    med = make_case(id="m", expect={"flags": ["medical"], "score": 0})
    results = [
        make_measured(ctx, a),  # all right
        make_measured(ctx, b, make_verdict(goals=Goals(True, True, True))),  # reassure wrong
        # medical case: model also flags off_topic (false positive) and finds medical
        make_measured(ctx, med, make_verdict(flags=("medical", "off_topic"))),
    ]
    m = compute_metrics(CONFIG, results, PRICES)
    acc = m.accuracy
    assert acc.goal_accuracy["notice"] == 1.0  # a, b
    assert acc.goal_accuracy["reassure"] == 0.5  # a right, b wrong
    assert acc.goal_accuracy["offer"] == 1.0  # a only
    assert acc.exact_score_rate == pytest.approx(2 / 3)  # a and med right; b scored 3, expected 2
    assert acc.argued_accuracy == 1.0
    assert acc.flag_recall == 1.0
    assert acc.flag_precision == 0.5  # 1 true of 2 predicted
    assert 0.0 <= acc.composite <= 1.0


def test_failed_call_counts_as_wrong_and_predicts_no_flags(ctx: EvalContext) -> None:
    med = make_case(id="m", expect={"flags": ["medical"], "score": 0})
    m = compute_metrics(CONFIG, [make_measured(ctx, med, error="CoachUnavailable")], PRICES)
    assert m.accuracy.exact_score_rate == 0.0
    assert m.accuracy.flag_recall == 0.0
    assert m.safety.recall == 0.0 and m.safety.missed_ids == ("m",)


def _verdict(notice: bool, flags: tuple[str, ...] = ()) -> CoachVerdict:
    return make_verdict(goals=Goals(notice, True, True), flags=flags)


def test_consistency_is_share_of_cases_with_same_goals_and_flags_across_3_runs(
    ctx: EvalContext,
) -> None:
    same, goals_differ, flags_differ, one_failed = (make_case(id=i) for i in "abcd")
    results = []
    for run in range(3):
        results.append(make_measured(ctx, same, _verdict(True), run=run))
        results.append(make_measured(ctx, goals_differ, _verdict(run != 1), run=run))
        results.append(
            make_measured(
                ctx, flags_differ, _verdict(True, ("off_topic",) if run == 2 else ()), run=run
            )
        )
        results.append(
            make_measured(
                ctx,
                one_failed,
                None if run == 0 else _verdict(True),
                run=run,
                error=None if run else "CoachUnavailable",
            )
        )
    share, runs = consistency(results)
    assert share == 0.25  # only "a" agrees in all three runs
    assert runs == 3
    # A text-only difference is NOT a disagreement.
    texts = [
        make_measured(ctx, same, make_verdict(tip=f"Tip number {i}."), run=i) for i in range(3)
    ]
    assert consistency(texts)[0] == 1.0
    # One run per case: not measurable.
    assert consistency(results[:4])[0] is None


def test_reliability_schema_refusal_timeout_rates(ctx: EvalContext) -> None:
    case = make_case()
    results = [
        make_measured(ctx, case, call=make_call()),
        make_measured(ctx, case, make_verdict(flags=("bogus",)), call=make_call()),  # schema
        make_measured(ctx, case, error="CoachUnavailable", call=make_call(outcome="refusal")),
        make_measured(ctx, case, error="CoachUnavailable", call=make_call(outcome="timeout")),
        make_measured(ctx, case, wall_ms=12_001.0, call=make_call()),  # slow: over the budget
        make_measured(ctx, case, error="CoachUnavailable", call=make_call(outcome="api_error")),
        make_measured(
            ctx, case, error="CoachUnavailable", call=make_call(outcome="invalid_output")
        ),
        make_measured(ctx, case, wall_ms=12_000.0, call=make_call()),  # exactly the budget: ok
        make_measured(ctx, case),
        make_measured(ctx, case),
    ]
    rel = compute_metrics(CONFIG, results, PRICES).reliability
    assert rel.calls == 10
    assert rel.schema_failure_rate == 0.2
    assert rel.refusal_rate == 0.1
    assert rel.timeout_rate == 0.2
    assert rel.other_failure_rate == 0.1


def test_latency_percentiles_use_nearest_rank(ctx: EvalContext) -> None:
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    assert percentile([7.0], 95) == 7.0
    case = make_case()
    results = [make_measured(ctx, case, wall_ms=float(ms)) for ms in range(100, 2100, 100)]
    lat = compute_metrics(CONFIG, results, PRICES, concurrency=4).latency
    assert (lat.p50_ms, lat.p95_ms, lat.max_ms, lat.concurrency) == (1000, 1900, 2000, 4)


def test_cost_per_turn_and_lesson_with_and_without_cache(ctx: EvalContext) -> None:
    case = make_case()
    warm = make_call(input_tokens=200, output_tokens=100, cache_read=800)
    cold = make_call(input_tokens=200, output_tokens=100, cache_write=800)
    results = [make_measured(ctx, case, call=warm), make_measured(ctx, case, call=cold)]
    cost = compute_metrics(CONFIG, results, PRICES).cost
    assert cost is not None
    # opus: $4 in, $20 out, $0.20 read, $5 write per MTok
    warm_usd = (200 * 4 + 800 * 0.2 + 100 * 20) / 1e6
    cold_usd = (200 * 4 + 800 * 5 + 100 * 20) / 1e6
    plain_usd = (1000 * 4 + 100 * 20) / 1e6
    assert cost.per_turn_usd == pytest.approx((warm_usd + cold_usd) / 2)
    assert cost.per_turn_usd_no_cache == pytest.approx(plain_usd)
    assert cost.per_lesson_usd == pytest.approx(3 * cost.per_turn_usd)
    assert cost.per_lesson_usd_no_cache == pytest.approx(3 * plain_usd)
    assert cost.priced_calls == 2
    assert compute_metrics(CONFIG, [make_measured(ctx, case)], PRICES).cost is None  # no usage


def test_quality_slot_may_be_absent_or_filled(ctx: EvalContext) -> None:
    m = compute_metrics(CONFIG, [make_measured(ctx, make_case())], PRICES)
    assert m.quality is None
    assert m.with_quality(0.8).quality == 0.8
    with pytest.raises(ValueError):
        m.with_quality(4.5)  # must be normalised 0-1


class _SlowCoach:
    """Records the peak concurrency and reports a distinct usage per case through the sink."""

    def __init__(self, recorder: CallRecorder) -> None:
        self.active = 0
        self.peak = 0
        self._recorder = recorder

    async def turn(self, coach_input: CoachInput) -> CoachVerdict:
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.01)
        self._recorder.sink(make_call(input_tokens=len(coach_input.caregiver_reply)))
        self.active -= 1
        return make_verdict()


async def test_runner_supports_sequential_and_4_concurrent_runs(ctx: EvalContext) -> None:
    cases = [make_case(id=f"c{i}", caregiverReply="x" * (i + 1)) for i in range(8)]
    for concurrency, expected_peak in ((1, 1), (4, 4)):
        recorder = CallRecorder()
        coach = _SlowCoach(recorder)
        out = await run_measured(
            coach, cases, ctx, runs=1, concurrency=concurrency, recorder=recorder
        )
        assert coach.peak == expected_peak
        assert [m.case.id for m in out] == [c.id for c in cases]
        # Each result carries ITS OWN usage even when calls overlap.
        assert [m.call.input_tokens for m in out if m.call] == [i + 1 for i in range(8)]
        assert all(m.wall_ms >= 10 for m in out)


def test_no_price_file_edits_needed_for_path(tmp_path: Path) -> None:
    bad = tmp_path / "p.json"
    bad.write_text("{}")
    with pytest.raises(PriceError):
        load_prices(bad)
