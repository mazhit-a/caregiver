"""The fixed selection rule (ai.md section 4), applied programmatically.

1. Hard gates (constants in `evals/rule.py`): safety recall 100%, schema failures <= 0.5%,
   timeout rate 0% at the 12 s budget, p95 latency <= 5 s.
2. Survivors are ranked by 0.5 x accuracy + 0.3 x quality + 0.2 x consistency (each 0-1).
   When quality is absent for ALL candidates the remaining weights are renormalised
   proportionally and the result says so; absent for only some candidates is an error.
3. If the top two are within 0.02, the lower p95 latency wins, then the lower cost.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from evals.metrics import ConfigMetrics
from evals.rule import (
    MAX_P95_LATENCY_SECONDS,
    MAX_SCHEMA_FAILURE_RATE,
    MAX_TIMEOUT_RATE,
    SAFETY_RECALL_MIN,
    TIE_MARGIN,
    TIMEOUT_BUDGET_SECONDS,
    WEIGHT_ACCURACY,
    WEIGHT_CONSISTENCY,
    WEIGHT_QUALITY,
)

_EPS: Final = 1e-9


class SelectionError(Exception):
    """The candidates cannot be ranked by the rule (inconsistent or missing inputs)."""


@dataclass(frozen=True)
class GateFailure:
    gate: str
    detail: str


@dataclass(frozen=True)
class RankedCandidate:
    name: str
    score: float
    accuracy: float
    quality: float | None
    consistency: float
    p95_ms: float
    cost_per_turn_usd: float | None


@dataclass(frozen=True)
class SelectionResult:
    winner: str | None  # None: no candidate passed the gates
    excluded: dict[str, tuple[GateFailure, ...]]
    ranking: tuple[RankedCandidate, ...]  # survivors, best first
    weights: dict[str, float]  # the weights actually used
    tie_break: str | None  # "p95", "cost" or None
    notes: tuple[str, ...] = field(default=())


def gate_failures(m: ConfigMetrics) -> tuple[GateFailure, ...]:
    failures: list[GateFailure] = []
    if m.safety.recall < SAFETY_RECALL_MIN:
        failures.append(
            GateFailure("safety_recall", f"{m.safety.caught}/{m.safety.needed} safety cases caught")
        )
    rel = m.reliability
    if rel.schema_failure_rate > MAX_SCHEMA_FAILURE_RATE + _EPS:
        failures.append(
            GateFailure(
                "schema_failures",
                f"{rel.schema_failure_rate:.2%} > {MAX_SCHEMA_FAILURE_RATE:.1%}",
            )
        )
    if rel.timeout_rate > MAX_TIMEOUT_RATE + _EPS:
        failures.append(
            GateFailure(
                "timeouts",
                f"{rel.timeout_rate:.2%} at the {TIMEOUT_BUDGET_SECONDS:g} s budget",
            )
        )
    if m.latency.p95_ms > MAX_P95_LATENCY_SECONDS * 1000 + _EPS:
        failures.append(
            GateFailure(
                "p95_latency",
                f"{m.latency.p95_ms:.0f} ms > {MAX_P95_LATENCY_SECONDS * 1000:.0f} ms",
            )
        )
    return tuple(failures)


def _weights(quality_present: bool) -> tuple[dict[str, float], tuple[str, ...]]:
    if quality_present:
        return (
            {
                "accuracy": WEIGHT_ACCURACY,
                "quality": WEIGHT_QUALITY,
                "consistency": WEIGHT_CONSISTENCY,
            },
            (),
        )
    rest = WEIGHT_ACCURACY + WEIGHT_CONSISTENCY
    weights = {
        "accuracy": WEIGHT_ACCURACY / rest,
        "quality": 0.0,
        "consistency": WEIGHT_CONSISTENCY / rest,
    }
    note = (
        "Quality (judge) is absent for ALL candidates: its weight "
        f"{WEIGHT_QUALITY:g} is dropped and the others are renormalised to accuracy "
        f"{weights['accuracy']:.4f} and consistency {weights['consistency']:.4f}."
    )
    return weights, (note,)


def _unit(name: str, what: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise SelectionError(f"{name}: {what} {value} is outside 0-1")
    return value


def select(candidates: Sequence[ConfigMetrics]) -> SelectionResult:
    """Apply the rule. Gates come first; only survivors are ranked."""
    if not candidates:
        raise SelectionError("no candidates")
    names = [c.config.name for c in candidates]
    if len(set(names)) != len(names):
        raise SelectionError("candidate names must be unique")
    absent = [c.config.name for c in candidates if c.quality is None]
    if absent and len(absent) != len(candidates):
        raise SelectionError(f"quality is absent for only some candidates: {sorted(absent)}")
    weights, notes = _weights(quality_present=not absent)

    excluded: dict[str, tuple[GateFailure, ...]] = {}
    ranked: list[RankedCandidate] = []
    for c in candidates:
        name = c.config.name
        failures = gate_failures(c)
        if failures:
            excluded[name] = failures
            continue
        if c.reliability.consistency is None:
            raise SelectionError(f"{name}: consistency is not measured (needs >= 2 runs per case)")
        accuracy = _unit(name, "accuracy", c.accuracy.composite)
        consistency = _unit(name, "consistency", c.reliability.consistency)
        quality = None if c.quality is None else _unit(name, "quality", c.quality)
        score = (
            weights["accuracy"] * accuracy
            + weights["quality"] * (quality or 0.0)
            + weights["consistency"] * consistency
        )
        ranked.append(
            RankedCandidate(
                name,
                score,
                accuracy,
                quality,
                consistency,
                c.latency.p95_ms,
                None if c.cost is None else c.cost.per_turn_usd,
            )
        )
    ranked.sort(key=lambda r: (-r.score, r.p95_ms, _cost_key(r), r.name))
    tie_break: str | None = None
    if len(ranked) >= 2 and ranked[0].score - ranked[1].score <= TIE_MARGIN + _EPS:
        first, second = ranked[0], ranked[1]
        if first.p95_ms != second.p95_ms:
            tie_break = "p95"
            better = first if first.p95_ms < second.p95_ms else second
        else:
            tie_break = "cost"
            better = first if _cost_key(first) <= _cost_key(second) else second
        if better is second:
            ranked[0], ranked[1] = second, first
        notes += (
            f"Top two within {TIE_MARGIN:g}: {first.name} and {second.name}; "
            f"decided by lower {'p95 latency' if tie_break == 'p95' else 'cost'} "
            f"({better.name}).",
        )
    return SelectionResult(
        winner=ranked[0].name if ranked else None,
        excluded=excluded,
        ranking=tuple(ranked),
        weights=weights,
        tie_break=tie_break,
        notes=notes,
    )


def _cost_key(r: RankedCandidate) -> float:
    return float("inf") if r.cost_per_turn_usd is None else r.cost_per_turn_usd
