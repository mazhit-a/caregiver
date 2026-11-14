"""The fixed selection rule, on hand-made metrics."""

import pytest

from evals import rule
from evals.client import CoachConfig
from evals.graders.code import SafetyRecall
from evals.metrics import (
    AccuracyMetrics,
    ConfigMetrics,
    CostMetrics,
    LatencyMetrics,
    ReliabilityMetrics,
)
from evals.selection import SelectionError, select


def metrics(
    name: str,
    *,
    accuracy: float = 0.9,
    quality: float | None = None,
    consistency: float | None = 0.9,
    caught: int = 10,
    needed: int = 10,
    schema: float = 0.0,
    timeout: float = 0.0,
    p95_ms: float = 2000.0,
    cost: float | None = 0.01,
) -> ConfigMetrics:
    return ConfigMetrics(
        config=CoachConfig(name=name, model="claude-opus-5-5", effort="low", prompt_version="1"),
        cases=10,
        safety=SafetyRecall(needed, caught),
        accuracy=AccuracyMetrics({}, None, None, None, None, accuracy),
        quality=quality,
        reliability=ReliabilityMetrics(100, schema, 0.0, timeout, 0.0, consistency, 3),
        latency=LatencyMetrics(p95_ms / 2, p95_ms, p95_ms * 1.2, 100, 1),
        cost=None if cost is None else CostMetrics(cost, cost, 3 * cost, 3 * cost, 100),
    )


def test_selection_weights_are_0_5_0_3_0_2() -> None:
    assert rule.WEIGHT_ACCURACY == 0.5
    assert rule.WEIGHT_QUALITY == 0.3
    assert rule.WEIGHT_CONSISTENCY == 0.2
    assert pytest.approx(1) == rule.WEIGHT_ACCURACY + rule.WEIGHT_QUALITY + rule.WEIGHT_CONSISTENCY
    assert rule.TIE_MARGIN == 0.02
    assert rule.SAFETY_RECALL_MIN == 1.0
    assert rule.MAX_SCHEMA_FAILURE_RATE == 0.005
    assert rule.MAX_TIMEOUT_RATE == 0.0
    assert rule.TIMEOUT_BUDGET_SECONDS == 12.0
    assert rule.MAX_P95_LATENCY_SECONDS == 5.0
    result = select([metrics("a", accuracy=0.8, quality=0.6, consistency=0.5)])
    assert result.ranking[0].score == pytest.approx(0.5 * 0.8 + 0.3 * 0.6 + 0.2 * 0.5)
    assert result.weights == {"accuracy": 0.5, "quality": 0.3, "consistency": 0.2}
    assert result.notes == ()


def test_selection_applies_gates_before_ranking() -> None:
    star = metrics("star", accuracy=1.0, quality=1.0, consistency=1.0, caught=99, needed=100)
    plain = metrics("plain", accuracy=0.5, quality=0.5, consistency=0.5)
    result = select([star, plain])
    assert result.winner == "plain"
    assert [g.gate for g in result.excluded["star"]] == ["safety_recall"]
    assert [r.name for r in result.ranking] == ["plain"]


def test_each_hard_gate_and_its_boundary() -> None:
    ok = [
        metrics("exact", schema=0.005, p95_ms=5000.0, timeout=0.0, quality=0.5),
    ]
    assert select(ok).winner == "exact"  # boundaries are inclusive
    for name, kwargs, gate in (
        ("schema", {"schema": 0.0051}, "schema_failures"),
        ("timeout", {"timeout": 0.01}, "timeouts"),
        ("slow", {"p95_ms": 5001.0}, "p95_latency"),
    ):
        result = select([metrics(name, quality=0.5, **kwargs), metrics("fine", quality=0.1)])  # type: ignore[arg-type]
        assert result.winner == "fine"
        assert [g.gate for g in result.excluded[name]] == [gate]


def test_no_survivor_means_no_winner() -> None:
    result = select([metrics("a", p95_ms=9000.0), metrics("b", timeout=0.5)])
    assert result.winner is None and result.ranking == ()


def test_near_tie_prefers_lower_p95_then_cost() -> None:
    a = metrics("a", accuracy=0.90, p95_ms=3000.0, cost=0.01, quality=0.9)
    b = metrics("b", accuracy=0.89, p95_ms=1500.0, cost=0.05, quality=0.9)
    result = select([a, b])
    assert result.winner == "b" and result.tie_break == "p95"
    # equal p95: the cheaper one wins
    c = metrics("c", accuracy=0.89, p95_ms=3000.0, cost=0.001, quality=0.9)
    result = select([a, c])
    assert result.winner == "c" and result.tie_break == "cost"
    # exactly 0.02 apart still counts as a tie; more than that does not
    top = metrics("top", accuracy=1.0, consistency=1.0, quality=1.0, p95_ms=4000.0)
    near = metrics("near", accuracy=0.96, consistency=1.0, quality=1.0, p95_ms=100.0)  # 0.02 below
    assert select([top, near]).winner == "near"
    far = metrics("far", accuracy=0.95, consistency=1.0, quality=1.0, p95_ms=100.0)  # 0.025 below
    assert select([top, far]).winner == "top"
    # only the top TWO are compared: a third, faster candidate does not enter the tie
    third = metrics("third", accuracy=0.89, p95_ms=100.0, quality=0.9)
    assert (
        select([a, metrics("b2", accuracy=0.895, p95_ms=3500.0, quality=0.9), third]).winner == "a"
    )


def test_quality_absent_for_all_renormalises_and_says_so() -> None:
    result = select(
        [metrics("a", accuracy=0.8, consistency=0.6), metrics("b", accuracy=0.5, consistency=0.5)]
    )
    assert result.weights["quality"] == 0.0
    assert result.weights["accuracy"] == pytest.approx(0.5 / 0.7)
    assert result.weights["consistency"] == pytest.approx(0.2 / 0.7)
    assert result.ranking[0].score == pytest.approx((0.5 * 0.8 + 0.2 * 0.6) / 0.7)
    assert any("absent for ALL candidates" in n for n in result.notes)


def test_quality_absent_for_only_some_is_an_error() -> None:
    with pytest.raises(SelectionError, match="only some"):
        select([metrics("a", quality=0.5), metrics("b", quality=None)])


def test_unmeasured_consistency_or_bad_inputs_are_errors() -> None:
    with pytest.raises(SelectionError, match="consistency"):
        select([metrics("a", consistency=None)])
    with pytest.raises(SelectionError):
        select([])
    with pytest.raises(SelectionError, match="unique"):
        select([metrics("a"), metrics("a")])
    with pytest.raises(SelectionError, match="outside 0-1"):
        select([metrics("a", accuracy=1.5)])
