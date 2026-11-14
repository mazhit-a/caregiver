"""Report writer: `evals/reports/<date>-<stage>.json` (raw per-case results) and `.md` (comparison
table, selection outcome, failures with reasons). Never writes model output text or caregiver
replies: only ids, numbers, flags and grader names with their short reasons.
"""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final

from evals import rule
from evals.metrics import ConfigMetrics, PriceTable
from evals.quality import QualityResult
from evals.runner import Measured
from evals.selection import SelectionResult

DEFAULT_REPORT_DIR: Final = Path(__file__).resolve().parent / "reports"
_STAGE = re.compile(r"^[A-Za-z0-9_\-]+$")


@dataclass(frozen=True)
class ConfigRun:
    """Everything one configuration contributes to a report."""

    metrics: ConfigMetrics
    measured: Sequence[Measured]
    fingerprint: Mapping[str, Any]
    quality: QualityResult | None = None  # judged quality detail; None when --judge was not used


def _case_rows(measured: Sequence[Measured]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for m in measured:
        o = m.result.outcome
        rows.append(
            {
                "caseId": m.result.case_id,
                "run": m.result.run_index,
                "cached": m.cached,
                "wallMs": m.wall_ms,
                "error": m.result.error,
                "callOutcome": m.call.outcome if m.call else None,
                "score": None if o is None else o.score,
                "goals": None if o is None else asdict(o.goals),
                "argued": None if o is None else o.argued,
                "flags": None if o is None else list(o.flags),
                "failedGrades": [
                    {"name": g.name, "detail": g.detail} for g in m.result.grades if not g.passed
                ],
                "tokens": None
                if m.call is None
                else {
                    "input": m.call.input_tokens,
                    "output": m.call.output_tokens,
                    "cacheRead": m.call.cache_read_tokens,
                    "cacheWrite": m.call.cache_creation_tokens,
                },
            }
        )
    return rows


def _judge_json(q: QualityResult) -> dict[str, Any]:
    """Numbers only: the judge's one-line reasons can quote model output, so they stay out."""
    out = asdict(q)
    out.pop("reasons", None)
    return out


def build_report(
    stage: str,
    runs: Sequence[ConfigRun],
    selection: SelectionResult | None,
    prices: PriceTable,
    *,
    dataset_split: str,
    on: date,
) -> dict[str, Any]:
    return {
        "date": on.isoformat(),
        "stage": stage,
        "split": dataset_split,
        "selectionRule": {
            "gates": {
                "safetyRecallMin": rule.SAFETY_RECALL_MIN,
                "maxSchemaFailureRate": rule.MAX_SCHEMA_FAILURE_RATE,
                "maxTimeoutRate": rule.MAX_TIMEOUT_RATE,
                "timeoutBudgetSeconds": rule.TIMEOUT_BUDGET_SECONDS,
                "maxP95LatencySeconds": rule.MAX_P95_LATENCY_SECONDS,
            },
            "weights": {
                "accuracy": rule.WEIGHT_ACCURACY,
                "quality": rule.WEIGHT_QUALITY,
                "consistency": rule.WEIGHT_CONSISTENCY,
            },
            "tieMargin": rule.TIE_MARGIN,
        },
        "prices": {"retrievedOn": prices.retrieved_on, "note": prices.note},
        "configs": [
            {
                "name": r.metrics.config.name,
                "fingerprint": dict(r.fingerprint),
                "metrics": asdict(r.metrics),
                "judge": None if r.quality is None else _judge_json(r.quality),
                "cases": _case_rows(r.measured),
            }
            for r in runs
        ],
        "selection": None if selection is None else asdict(selection),
    }


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.1%}"


def _usd(v: float | None) -> str:
    return "n/a" if v is None else f"${v:.5f}"


def render_markdown(
    report: Mapping[str, Any], runs: Sequence[ConfigRun], selection: SelectionResult | None
) -> str:
    out = [f"# Eval report: {report['stage']} ({report['date']}, {report['split']} set)", ""]
    out += [
        "| config | safety recall | accuracy | quality | consistency | schema fail | refusal | "
        "timeout | p50 / p95 / max ms | $/turn | $/lesson | $/lesson no cache |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in runs:
        m = r.metrics
        c = m.cost
        out.append(
            f"| {m.config.name} | {_pct(m.safety.recall)} ({m.safety.caught}/{m.safety.needed}) "
            f"| {_pct(m.accuracy.composite)} | {_pct(m.quality)} "
            f"| {_pct(m.reliability.consistency)} "
            f"| {_pct(m.reliability.schema_failure_rate)} | {_pct(m.reliability.refusal_rate)} "
            f"| {_pct(m.reliability.timeout_rate)} "
            f"| {m.latency.p50_ms:.0f} / {m.latency.p95_ms:.0f} / {m.latency.max_ms:.0f} "
            f"(x{m.latency.concurrency}) "
            f"| {_usd(c.per_turn_usd if c else None)} | {_usd(c.per_lesson_usd if c else None)} "
            f"| {_usd(c.per_lesson_usd_no_cache if c else None)} |"
        )
    out += [
        "",
        "Accuracy is the mean of: mean per-goal accuracy, exact-score rate, argued accuracy, "
        "flag F1 (components with no applicable case are left out).",
        "",
    ]
    for r in runs:
        a = r.metrics.accuracy
        goals = ", ".join(f"{k} {_pct(v)}" for k, v in a.goal_accuracy.items())
        out.append(
            f"- {r.metrics.config.name}: goals {goals}; exact score {_pct(a.exact_score_rate)}; "
            f"argued {_pct(a.argued_accuracy)}; flag precision {_pct(a.flag_precision)}, "
            f"recall {_pct(a.flag_recall)}"
        )
    judged = [r for r in runs if r.quality is not None]
    if judged:
        out += ["", "## Judged quality", ""]
        for r in judged:
            q = r.quality
            assert q is not None  # noqa: S101 - filtered above
            items = ", ".join(f"{k} {_pct(v)}" for k, v in q.per_item.items())
            skipped = ", ".join(f"{k} {n}" for k, n in q.unjudged.items()) or "none"
            out.append(
                f"- {r.metrics.config.name}: quality {_pct(q.quality)} ({items}); "
                f"{q.judged} judged, unjudged: {skipped}; judge {q.judge_model} "
                f"{q.judge_effort}, prompt {q.judge_prompt_version}, {q.calls} calls"
            )
    out += ["", "## Selection", ""]
    if selection is None:
        out.append("Not applied (single exploratory run).")
    else:
        w = selection.weights
        out.append(
            f"Weights used: accuracy {w['accuracy']:.4f}, quality {w['quality']:.4f}, "
            f"consistency {w['consistency']:.4f}."
        )
        out.append(f"**Winner: {selection.winner or 'none (no candidate passed the gates)'}**")
        for name, failures in selection.excluded.items():
            out.append(
                f"- excluded {name}: " + "; ".join(f"{f.gate} ({f.detail})" for f in failures)
            )
        for i, rc in enumerate(selection.ranking, 1):
            out.append(f"{i}. {rc.name}: score {rc.score:.4f}, p95 {rc.p95_ms:.0f} ms")
        out += [f"- note: {n}" for n in selection.notes]
    out += ["", "## Failures", ""]
    any_failure = False
    for r in runs:
        for row in _case_rows(r.measured):
            if row["failedGrades"] or row["error"]:
                any_failure = True
                reasons = "; ".join(f"{g['name']}: {g['detail']}" for g in row["failedGrades"])
                out.append(
                    f"- {r.metrics.config.name} / {row['caseId']} run {row['run']}: "
                    f"{row['error'] or ''} {reasons}".rstrip()
                )
    if not any_failure:
        out.append("None.")
    out += [
        "",
        f"Prices retrieved on {report['prices']['retrievedOn']}: {report['prices']['note']}",
        "",
    ]
    return "\n".join(out)


def write_report(
    stage: str,
    runs: Sequence[ConfigRun],
    selection: SelectionResult | None,
    prices: PriceTable,
    *,
    dataset_split: str,
    on: date | None = None,
    out_dir: Path = DEFAULT_REPORT_DIR,
) -> tuple[Path, Path]:
    """Writes `<date>-<stage>.json` and `.md`; returns (json_path, md_path)."""
    if not _STAGE.match(stage):
        raise ValueError(f"invalid stage name {stage!r}")
    when = on or date.today()
    report = build_report(stage, runs, selection, prices, dataset_split=dataset_split, on=when)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"{when.isoformat()}-{stage}"
    json_path, md_path = base.with_suffix(".json"), base.with_suffix(".md")
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_markdown(report, runs, selection), encoding="utf-8")
    return json_path, md_path
