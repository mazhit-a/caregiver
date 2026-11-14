"""Judge calibration: `python -m evals.calibrate`.

Runs the judge over the human-labelled outputs in `evals/datasets/human_labels.jsonl` and reports
AGREEMENT: the share of (label, rubric item) pairs where the judge score is within +-1 of the human
score (exact match is also reported, but is not the gate). A judge call that failed counts as a
disagreement. The judge PASSES when overall agreement and the agreement of every rubric item are
>= 80% (the plan's threshold; the per-item condition is stricter so a bad item cannot hide behind a
good one). Exit code 0 = pass, non-zero otherwise.

The report is written to `evals/reports/calibration/` and is the ONLY thing that unlocks judged
`quality`: `require_calibration()` refuses a judge prompt file, model or effort that has no passing
report (see `evals/quality.py`). Real runs use the increment-20 cost estimate and confirmation gate.
"""

import argparse
import asyncio
import hashlib
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final

from app.infrastructure.config import Settings
from evals.client import ModelClient, real_client
from evals.cost import confirm_run, format_estimate
from evals.graders.judge import (
    EFFORTS,
    JUDGE_EFFORT,
    JUDGE_PROMPT_VERSION,
    RUBRIC_ITEMS,
    Judge,
    JudgePrompt,
    JudgePromptError,
    JudgeUnavailable,
    load_judge_prompt,
)
from evals.judge_cost import estimate_judge_run
from evals.labels import HUMAN_LABELS_PATH, MIN_LABELS, HumanLabel, LabelError, load_labels
from evals.metrics import PriceError, load_prices

AGREEMENT_THRESHOLD: Final = 0.8
TOLERANCE: Final = 1
REPORT_FORMAT: Final = 1
CALIBRATION_DIR: Final = Path(__file__).resolve().parent / "reports" / "calibration"
AGREEMENT_DEFINITION: Final = (
    "agreement = share of (label, rubric item) pairs where |judge score - human score| <= 1 "
    "(scores 1-5); a failed judge call is a disagreement; the judge passes when overall and every "
    "rubric item are >= 80%. Exact-match share is reported but is not the gate."
)
EXIT_REFUSED: Final = 3


class JudgeNotCalibrated(Exception):
    """No passing calibration report exists for this judge prompt file, model and effort."""


@dataclass(frozen=True)
class RowResult:
    label_id: str
    human: dict[str, int]
    judge: dict[str, int] | None  # None: the judge call failed


@dataclass(frozen=True)
class Agreement:
    pairs: int
    within_one: int
    exact: int

    @property
    def rate(self) -> float:
        return self.within_one / self.pairs if self.pairs else 0.0

    @property
    def exact_rate(self) -> float:
        return self.exact / self.pairs if self.pairs else 0.0


def _agree(rows: Sequence[RowResult], items: Sequence[str]) -> Agreement:
    pairs = within = exact = 0
    for row in rows:
        for item in items:
            pairs += 1
            if row.judge is None:
                continue
            diff = abs(row.judge[item] - row.human[item])
            within += int(diff <= TOLERANCE)
            exact += int(diff == 0)
    return Agreement(pairs, within, exact)


def compute_agreement(rows: Sequence[RowResult]) -> tuple[Agreement, dict[str, Agreement]]:
    """(overall, per rubric item). Pure."""
    return _agree(rows, RUBRIC_ITEMS), {item: _agree(rows, (item,)) for item in RUBRIC_ITEMS}


def passes(overall: Agreement, per_item: dict[str, Agreement]) -> bool:
    return overall.rate >= AGREEMENT_THRESHOLD and all(
        a.rate >= AGREEMENT_THRESHOLD for a in per_item.values()
    )


async def judge_rows(
    labels: Sequence[HumanLabel], judge: Judge, *, concurrency: int = 1
) -> list[RowResult]:
    gate = asyncio.Semaphore(concurrency)

    async def one(label: HumanLabel) -> RowResult:
        async with gate:
            try:
                result = await judge.judge(label.to_item())
            except JudgeUnavailable:
                return RowResult(label.id, label.human_scores(), None)
            return RowResult(label.id, label.human_scores(), result.scores)

    return list(await asyncio.gather(*(one(label) for label in labels)))


def build_calibration_report(
    rows: Sequence[RowResult],
    *,
    prompt: JudgePrompt,
    model: str,
    effort: str,
    labels_sha256: str,
    on: date,
) -> dict[str, Any]:
    overall, per_item = compute_agreement(rows)

    def block(a: Agreement) -> dict[str, Any]:
        return {
            "pairs": a.pairs,
            "withinOne": a.within_one,
            "agreement": a.rate,
            "exactMatch": a.exact_rate,
        }

    return {
        "format": REPORT_FORMAT,
        "generatedOn": on.isoformat(),
        "judgePromptVersion": prompt.version,
        "judgePromptSha256": prompt.sha256,
        "judgeModel": model,
        "judgeEffort": effort,
        "labelsSha256": labels_sha256,
        "labelCount": len(rows),
        "judgeFailures": sum(1 for r in rows if r.judge is None),
        "agreementDefinition": AGREEMENT_DEFINITION,
        "tolerance": TOLERANCE,
        "threshold": AGREEMENT_THRESHOLD,
        "overall": block(overall),
        "perItem": {k: block(v) for k, v in per_item.items()},
        "passed": passes(overall, per_item),
        "rows": [{"id": r.label_id, "human": r.human, "judge": r.judge} for r in rows],
    }


def report_path(directory: Path, prompt_version: str, model: str, effort: str) -> Path:
    return directory / f"judge-{prompt_version}-{model}-{effort}.json"


def write_calibration_report(report: dict[str, Any], directory: Path = CALIBRATION_DIR) -> Path:
    path = report_path(
        directory, report["judgePromptVersion"], report["judgeModel"], report["judgeEffort"]
    )
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def require_calibration(
    prompt: JudgePrompt, model: str, effort: str, directory: Path = CALIBRATION_DIR
) -> dict[str, Any]:
    """The gate. Returns the passing report or raises `JudgeNotCalibrated`. The numbers are
    re-checked here, not just the `passed` flag, and the prompt FILE hash must match, so editing
    the judge prompt invalidates the calibration."""
    path = report_path(directory, prompt.version, model, effort)
    try:
        report: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise JudgeNotCalibrated(
            f"no calibration report for judge prompt {prompt.version}, model {model}, effort "
            f"{effort}: run `python -m evals.calibrate` with human labels"
        ) from None
    try:
        problems: list[str] = []
        if report["format"] != REPORT_FORMAT:
            problems.append("unknown report format")
        if report["judgePromptSha256"] != prompt.sha256:
            problems.append("the judge prompt file changed since calibration")
        if (report["judgeModel"], report["judgeEffort"]) != (model, effort):
            problems.append("model or effort differs")
        if report["labelCount"] < MIN_LABELS:
            problems.append(f"fewer than {MIN_LABELS} labels")
        rates = [report["overall"]["agreement"]] + [
            report["perItem"][i]["agreement"] for i in RUBRIC_ITEMS
        ]
        if not report["passed"] or min(rates) < AGREEMENT_THRESHOLD:
            problems.append(
                f"agreement {min(rates):.0%} is below the {AGREEMENT_THRESHOLD:.0%} threshold"
            )
    except (KeyError, TypeError):
        raise JudgeNotCalibrated(f"calibration report {path.name} is malformed") from None
    if problems:
        raise JudgeNotCalibrated(f"judge is blocked: {'; '.join(problems)}")
    return report


# ------------------------------------------------------------------ CLI


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    client_factory: Callable[[Settings], ModelClient | None] = real_client,
    input_fn: Callable[[str], str] = input,
    interactive: bool | None = None,
    today: date | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.calibrate", description=__doc__)
    parser.add_argument("--labels", type=Path, default=HUMAN_LABELS_PATH)
    parser.add_argument("--report-dir", type=Path, default=CALIBRATION_DIR)
    parser.add_argument("--prompt-version", default=JUDGE_PROMPT_VERSION)
    parser.add_argument("--model", default=None, help="default: EVAL_JUDGE_MODEL")
    parser.add_argument("--effort", default=JUDGE_EFFORT, choices=EFFORTS)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="print the estimate and exit")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--max-cost-usd", type=float, default=None)
    args = parser.parse_args(argv)
    if args.concurrency < 1:
        print("--concurrency must be at least 1", file=sys.stderr)
        return 1
    settings = settings or Settings()
    model: str = args.model or settings.eval_judge_model
    try:
        labels = load_labels(args.labels)
        prompt = load_judge_prompt(args.prompt_version)
        prices = load_prices()
        estimate = estimate_judge_run(
            [x.to_item() for x in labels],
            prompt,
            model=model,
            effort=args.effort,
            prices=prices,
        )
    except (LabelError, JudgePromptError, PriceError, OSError, ValueError) as exc:
        print(f"cannot calibrate: {exc}", file=sys.stderr)
        return 1
    print(format_estimate(estimate, 1, len(labels)))
    if args.dry_run:
        print("Dry run: no model call was made.")
        return 0
    client = client_factory(settings)
    if client is None:
        print("No ANTHROPIC_API_KEY: cannot make real calls.", file=sys.stderr)
        return EXIT_REFUSED
    is_tty = sys.stdin.isatty() if interactive is None else interactive
    decision = confirm_run(
        estimate,
        yes=args.yes,
        max_cost_usd=args.max_cost_usd,
        interactive=is_tty,
        input_fn=input_fn,
    )
    if not decision.approved:
        print(f"Refused: {decision.reason}. No model call was made.", file=sys.stderr)
        return EXIT_REFUSED
    judge = Judge(client, prompt=prompt, model=model, effort=args.effort)
    rows = asyncio.run(judge_rows(labels, judge, concurrency=args.concurrency))
    report = build_calibration_report(
        rows,
        prompt=prompt,
        model=model,
        effort=args.effort,
        labels_sha256=hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        on=today or date.today(),
    )
    path = write_calibration_report(report, args.report_dir)
    print(AGREEMENT_DEFINITION)
    o = report["overall"]
    print(
        f"overall agreement {o['agreement']:.1%} (exact {o['exactMatch']:.1%}) "
        f"on {report['labelCount']} labels, {report['judgeFailures']} judge failures"
    )
    for item, block in report["perItem"].items():
        print(f"  {item:<16} agreement {block['agreement']:.1%} (exact {block['exactMatch']:.1%})")
    verdict = "PASS" if report["passed"] else "FAIL: this judge must be fixed before it is used"
    print(f"{verdict}; report: {path}")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
