"""Per-configuration metrics from measured case runs (ai.md section 4). Pure functions: no model
call, no clock. Inputs are `Measured` records (see `runner.py`); prices: `data/prices.json`.
"""

import json
import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from app.domain.roleplay.verdict import CoachOutcome
from app.infrastructure.llm.anthropic_coach import CallMetrics
from evals.case import EvalCase
from evals.client import CoachConfig
from evals.graders.code import SafetyRecall, safety_recall
from evals.rule import LESSON_TURNS, TIMEOUT_BUDGET_SECONDS
from evals.runner import Measured

PRICES_PATH: Final = Path(__file__).resolve().parent / "data" / "prices.json"
SCHEMA_FAILURE_OUTCOMES: Final = frozenset({"invalid_output", "max_tokens"})
GOAL_NAMES: Final = ("notice", "reassure", "offer")


class PriceError(Exception):
    """No price for a model, or the price file is malformed."""


@dataclass(frozen=True)
class ModelPrice:
    input_per_mtok: float
    output_per_mtok: float
    cache_read_per_mtok: float
    cache_write_per_mtok: float


@dataclass(frozen=True)
class PriceTable:
    retrieved_on: str
    note: str
    models: dict[str, ModelPrice]

    def price(self, model: str) -> ModelPrice:
        found = self.models.get(model)
        if found is None:
            raise PriceError(f"No price for model {model!r} in the price table")
        return found


def load_prices(path: Path = PRICES_PATH) -> PriceTable:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    try:
        models = {
            name: ModelPrice(
                float(p["inputPerMTok"]),
                float(p["outputPerMTok"]),
                float(p["cacheReadPerMTok"]),
                float(p["cacheWritePerMTok"]),
            )
            for name, p in raw["models"].items()
        }
        return PriceTable(str(raw["retrievedOn"]), str(raw["note"]), models)
    except (KeyError, TypeError, ValueError) as exc:
        raise PriceError(f"Malformed price table {path}: {exc}") from exc


# ------------------------------------------------------------------ result types


@dataclass(frozen=True)
class AccuracyMetrics:
    goal_accuracy: dict[str, float | None]  # notice / reassure / offer
    exact_score_rate: float | None
    argued_accuracy: float | None
    flag_precision: float | None
    flag_recall: float | None
    composite: float  # 0-1, input to the selection rule (see `composite_accuracy`)


@dataclass(frozen=True)
class ReliabilityMetrics:
    calls: int
    schema_failure_rate: float
    refusal_rate: float
    timeout_rate: float
    other_failure_rate: float  # api error, no key: counted, not gated
    consistency: float | None  # None when no case has at least 2 runs
    runs_per_case: int


@dataclass(frozen=True)
class LatencyMetrics:
    p50_ms: float
    p95_ms: float
    max_ms: float
    samples: int
    concurrency: int  # 1 = live sequential, 4 = live at production concurrency


@dataclass(frozen=True)
class CostMetrics:
    per_turn_usd: float  # with the cache hits that actually happened
    per_turn_usd_no_cache: float  # every input token at the full input price
    per_lesson_usd: float
    per_lesson_usd_no_cache: float
    priced_calls: int


@dataclass(frozen=True)
class ConfigMetrics:
    config: CoachConfig
    cases: int
    safety: SafetyRecall
    accuracy: AccuracyMetrics
    quality: float | None  # normalised 0-1; None until the judge (increment 21) fills it
    reliability: ReliabilityMetrics
    latency: LatencyMetrics
    cost: CostMetrics | None  # None when no call carried usage (fake coach)

    def with_quality(self, quality: float | None) -> "ConfigMetrics":
        if quality is not None and not 0.0 <= quality <= 1.0:
            raise ValueError("quality must be normalised to 0-1")
        return ConfigMetrics(
            self.config,
            self.cases,
            self.safety,
            self.accuracy,
            quality,
            self.reliability,
            self.latency,
            self.cost,
        )


# ------------------------------------------------------------------ helpers


def _rate(hits: int, total: int) -> float | None:
    return None if total == 0 else hits / total


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile (p in 0-100); no interpolation, so it is a value that occurred."""
    if not values:
        raise ValueError("percentile of no values")
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


# ------------------------------------------------------------------ accuracy


def accuracy_metrics(measured: Sequence[Measured]) -> AccuracyMetrics:
    """A failed call (no outcome) is wrong for every applicable item and predicts no flags."""
    goal_hits: dict[str, list[int]] = {g: [0, 0] for g in GOAL_NAMES}
    score_hits = [0, 0]
    argued_hits = [0, 0]
    tp = fp = fn = 0
    for m in measured:
        case: EvalCase = m.case
        outcome: CoachOutcome | None = m.result.outcome
        for g in GOAL_NAMES:
            want = getattr(case.expect.goals, g)
            if want is not None:
                goal_hits[g][1] += 1
                if outcome is not None and getattr(outcome.goals, g) == want:
                    goal_hits[g][0] += 1
        if case.expect.score is not None:
            score_hits[1] += 1
            score_hits[0] += int(outcome is not None and outcome.score == case.expect.score)
        if case.expect.argued is not None:
            argued_hits[1] += 1
            argued_hits[0] += int(outcome is not None and outcome.argued == case.expect.argued)
        expected = set(case.expect.flags)
        got = set(outcome.flags) if outcome is not None else set()
        tp += len(expected & got)
        fp += len(got - expected)
        fn += len(expected - got)
    goal_accuracy = {g: _rate(h, n) for g, (h, n) in goal_hits.items()}
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    return AccuracyMetrics(
        goal_accuracy=goal_accuracy,
        exact_score_rate=_rate(*score_hits),
        argued_accuracy=_rate(*argued_hits),
        flag_precision=precision,
        flag_recall=recall,
        composite=composite_accuracy(
            goal_accuracy, _rate(*score_hits), _rate(*argued_hits), tp, fp, fn
        ),
    )


def composite_accuracy(
    goal_accuracy: dict[str, float | None],
    exact_score_rate: float | None,
    argued_accuracy: float | None,
    tp: int,
    fp: int,
    fn: int,
) -> float:
    """The single 0-1 accuracy used by the selection rule: the mean of the components that apply
    to at least one case: mean per-goal accuracy, exact-score rate, argued accuracy, flag F1.
    (The rule fixes the weights, not this composite; it is recorded in every report.)"""
    goals = [v for v in goal_accuracy.values() if v is not None]
    parts: list[float] = []
    if goals:
        parts.append(sum(goals) / len(goals))
    if exact_score_rate is not None:
        parts.append(exact_score_rate)
    if argued_accuracy is not None:
        parts.append(argued_accuracy)
    if tp + fp + fn > 0:
        parts.append(2 * tp / (2 * tp + fp + fn))
    return sum(parts) / len(parts) if parts else 0.0


# ------------------------------------------------------------------ reliability


def _signature(m: Measured) -> tuple[tuple[bool, bool, bool], tuple[str, ...]] | None:
    outcome = m.result.outcome
    if outcome is None:
        return None
    g = outcome.goals
    return ((g.notice, g.reassure, g.offer), tuple(sorted(outcome.flags)))


def consistency(measured: Sequence[Measured]) -> tuple[float | None, int]:
    """Share of cases whose goals AND flags are identical across all their runs. A failed run
    counts as a disagreement. Cases with a single run are not comparable and are left out.
    Returns (share, runs per case)."""
    by_case: dict[str, list[Measured]] = defaultdict(list)
    for m in measured:
        by_case[m.result.case_id].append(m)
    comparable = {k: v for k, v in by_case.items() if len(v) >= 2}
    if not comparable:
        return None, 1
    same = 0
    for runs in comparable.values():
        sigs = [_signature(r) for r in runs]
        if sigs[0] is not None and all(s == sigs[0] for s in sigs):
            same += 1
    return same / len(comparable), max(len(v) for v in comparable.values())


def is_timeout(m: Measured, budget_s: float) -> bool:
    return (m.call is not None and m.call.outcome == "timeout") or m.wall_ms > budget_s * 1000


def reliability_metrics(
    measured: Sequence[Measured], *, timeout_budget_s: float = TIMEOUT_BUDGET_SECONDS
) -> ReliabilityMetrics:
    n = len(measured)
    schema = refusal = timeout = other = 0
    for m in measured:
        outcome = m.call.outcome if m.call is not None else None
        timed_out = is_timeout(m, timeout_budget_s)
        is_schema = m.result.error == "InvalidCoachOutput" or outcome in SCHEMA_FAILURE_OUTCOMES
        is_refusal = outcome == "refusal"
        timeout += int(timed_out)
        schema += int(is_schema and not timed_out)
        refusal += int(is_refusal)
        failed = m.result.outcome is None
        other += int(failed and not (timed_out or is_schema or is_refusal))
    share, runs = consistency(measured)
    return ReliabilityMetrics(
        calls=n,
        schema_failure_rate=schema / n if n else 0.0,
        refusal_rate=refusal / n if n else 0.0,
        timeout_rate=timeout / n if n else 0.0,
        other_failure_rate=other / n if n else 0.0,
        consistency=share,
        runs_per_case=runs,
    )


# ------------------------------------------------------------------ latency and cost


def latency_metrics(measured: Sequence[Measured], concurrency: int = 1) -> LatencyMetrics:
    values = [m.wall_ms for m in measured]
    return LatencyMetrics(
        p50_ms=percentile(values, 50),
        p95_ms=percentile(values, 95),
        max_ms=max(values),
        samples=len(values),
        concurrency=concurrency,
    )


def _one_call_usd(c: CallMetrics, prices: PriceTable, *, with_cache: bool) -> float:
    p = prices.price(c.model)
    if with_cache:
        input_cost = (
            c.input_tokens * p.input_per_mtok
            + c.cache_read_tokens * p.cache_read_per_mtok
            + c.cache_creation_tokens * p.cache_write_per_mtok
        )
    else:
        input_cost = (
            c.input_tokens + c.cache_read_tokens + c.cache_creation_tokens
        ) * p.input_per_mtok
    return (input_cost + c.output_tokens * p.output_per_mtok) / 1_000_000


def call_cost_usd(m: Measured, prices: PriceTable, *, with_cache: bool) -> float | None:
    """USD for one case from its usage: the SUM over all its model calls (parallel_split pays for
    the coach call and the parent call, each at its own model's price). Without cache: cache reads
    and writes are charged as plain input tokens."""
    calls = m.usage_calls
    if not calls:
        return None
    return sum(_one_call_usd(c, prices, with_cache=with_cache) for c in calls)


def cost_metrics(measured: Sequence[Measured], prices: PriceTable) -> CostMetrics | None:
    """Mean over the calls that carry usage. Failed calls that burned tokens are included."""
    with_c = [v for m in measured if (v := call_cost_usd(m, prices, with_cache=True)) is not None]
    without = [v for m in measured if (v := call_cost_usd(m, prices, with_cache=False)) is not None]
    if not with_c:
        return None
    turn, turn_nc = sum(with_c) / len(with_c), sum(without) / len(without)
    return CostMetrics(turn, turn_nc, turn * LESSON_TURNS, turn_nc * LESSON_TURNS, len(with_c))


# ------------------------------------------------------------------ all together


def compute_metrics(
    config: CoachConfig,
    measured: Sequence[Measured],
    prices: PriceTable,
    *,
    quality: float | None = None,
    concurrency: int = 1,
    timeout_budget_s: float = TIMEOUT_BUDGET_SECONDS,
) -> ConfigMetrics:
    if not measured:
        raise ValueError("no measured results")
    recall = safety_recall([(m.case, m.result.outcome) for m in measured])
    metrics = ConfigMetrics(
        config=config,
        cases=len({m.result.case_id for m in measured}),
        safety=recall,
        accuracy=accuracy_metrics(measured),
        quality=None,
        reliability=reliability_metrics(measured, timeout_budget_s=timeout_budget_s),
        latency=latency_metrics(measured, concurrency),
        cost=cost_metrics(measured, prices),
    )
    return metrics.with_quality(quality)
