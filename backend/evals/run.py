"""Eval runner CLI. `uv run python -m evals.run --help` works offline.

A run that would call a real model first prints a cost estimate and needs confirmation (see
`evals/cost.py`). `--dry-run` prints the estimate and exits. `--judge` adds the model judge: its
calls are part of the same estimate and the same single confirmation (`--max-cost-usd` covers the
total). Results are cached, so only what
changed is called. The real-model path is implemented here but pytest only drives it with fakes.

TODO(batches): `--batch` (Message Batches API, 50% cheaper, accuracy-only runs; latency stays
live) needs real client code and is not implemented: the flag is accepted and refused.
"""

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from app.infrastructure.config import Settings
from app.infrastructure.llm.prompt import PromptLoadError
from evals.cache import DEFAULT_CACHE_DIR, ResultCache, config_fingerprint, fingerprint_parts
from evals.calibrate import CALIBRATION_DIR, JudgeNotCalibrated, require_calibration
from evals.case import EvalCase
from evals.client import CoachConfig, ModelClient, build_eval_coach, production_config, real_client
from evals.configs import STAGES, candidate, candidate_names
from evals.cost import (
    CostEstimate,
    confirm_run,
    estimate_run,
    format_estimate,
    table_token_estimate,
)
from evals.dataset import (
    GOLDEN_PATH,
    DatasetError,
    Split,
    load_all_acknowledging_test,
    load_split,
    split_summary,
)
from evals.graders.judge import (
    EFFORTS as JUDGE_EFFORTS,
)
from evals.graders.judge import (
    JUDGE_EFFORT,
    JUDGE_PROMPT_VERSION,
    Judge,
    JudgeItem,
    JudgePrompt,
    JudgePromptError,
    load_judge_prompt,
)
from evals.judge_cost import estimate_judge_run
from evals.metrics import ConfigMetrics, PriceError, PriceTable, compute_metrics, load_prices
from evals.quality import QualityResult, judge_measured, with_judged_quality
from evals.report import DEFAULT_REPORT_DIR, ConfigRun, write_report
from evals.rule import CONSISTENCY_RUNS, TIMEOUT_BUDGET_SECONDS
from evals.runner import CallRecorder, load_context, run_measured
from evals.selection import SelectionError, SelectionResult, select

EXIT_REFUSED = 2
EXIT_JUDGE_BLOCKED = 3  # --judge without a passing calibration report: stopped before any call

# Stand-ins for the coach's written output when ESTIMATING the judge calls before the coach has
# run (a typical length of each field; the real run judges the real output).
_TYPICAL_TIP = "You named the worry and offered something to do. Next time, say it once, slowly."
_TYPICAL_PHRASE = "Mom, you sound worried. I'm here with you. Would you like some tea?"
_TYPICAL_REACTION = "Tea sounds nice. Thank you, dear."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evals.run",
        description=(
            "Role-play eval runner: runs cases through the production coach and domain rules and "
            "grades them with code-based graders. REAL model calls cost money."
        ),
    )
    parser.add_argument(
        "--config",
        nargs="+",
        default=None,
        help=f"configurations: production or {', '.join(candidate_names())} (default production)",
    )
    parser.add_argument(
        "--stage",
        default="adhoc",
        help=f"report name; {', '.join(STAGES)} also select that stage's configurations",
    )
    parser.add_argument("--prompt-version", default=None, help="prompt version for candidates")
    parser.add_argument("--runs", type=int, default=CONSISTENCY_RUNS, help="runs per case")
    parser.add_argument(
        "--concurrency", type=int, default=1, help="live concurrency (1 sequential, 4 = production)"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the estimate and exit")
    parser.add_argument("--yes", action="store_true", help="skip the prompt (see --max-cost-usd)")
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=None,
        help="refuse above this estimate; required for --yes without a terminal",
    )
    parser.add_argument("--no-cache", action="store_true", help="ignore and do not write the cache")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument(
        "--judge",
        action="store_true",
        help=(
            "also grade each coached output with the model judge (adds its calls to the estimate "
            "and the confirmation; needs a passing calibration report, else exit code 3 before "
            "any call). Without it quality stays absent and selection renormalises."
        ),
    )
    parser.add_argument("--judge-model", default=None, help="default: EVAL_JUDGE_MODEL")
    parser.add_argument("--judge-effort", default=JUDGE_EFFORT, choices=JUDGE_EFFORTS)
    parser.add_argument("--judge-prompt-version", default=JUDGE_PROMPT_VERSION)
    parser.add_argument(
        "--calibration-dir", type=Path, default=CALIBRATION_DIR, help="judge calibration reports"
    )
    parser.add_argument("--batch", action="store_true", help="Batches API (not implemented, TODO)")
    parser.add_argument(
        "--set",
        dest="split",
        choices=[s.value for s in Split],
        default="dev",
        help="dataset split (test is held out: use it once per final comparison)",
    )
    parser.add_argument(
        "--dataset", type=Path, nargs="+", default=[GOLDEN_PATH], help="JSONL dataset file(s)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="load and validate the dataset, print split counts, make no model call",
    )
    return parser


def _resolve_configs(args: argparse.Namespace, settings: Settings) -> list[CoachConfig]:
    names: Sequence[str] = args.config or STAGES.get(args.stage, ("production",))
    version = args.prompt_version or settings.coach_prompt_version
    configs: list[CoachConfig] = []
    for name in names:
        configs.append(
            production_config(settings) if name == "production" else candidate(name, version)
        )
    return configs


def _judge_estimate(
    cases: Sequence[EvalCase],
    prompt: JudgePrompt,
    model: str,
    effort: str,
    calls: int,
    prices: PriceTable,
) -> CostEstimate:
    """Worst case: one judge call per case x run x configuration (judging is not cached)."""
    items = [
        JudgeItem(
            label=c.label,
            parent_line=c.parent_line,
            parent_mood=c.parent_mood,
            caregiver_reply=c.caregiver_reply,
            tip=_TYPICAL_TIP,
            better_phrase=_TYPICAL_PHRASE,
            parent_reaction=_TYPICAL_REACTION,
            coach_parent_mood="calmer",
            coach_score=2,
            previous_turns=tuple((t.parent, t.caregiver) for t in c.previous_turns),
        )
        for c in cases
    ]
    return estimate_judge_run(items, prompt, model=model, effort=effort, prices=prices, calls=calls)


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    client_factory: Callable[[Settings], ModelClient | None] = real_client,
    input_fn: Callable[[str], str] = input,
    interactive: bool | None = None,
    today: date | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        cases = load_split(Split(args.split), args.dataset)
        everything = load_all_acknowledging_test(args.dataset, i_know_this_uses_the_test_set=True)
    except DatasetError as exc:
        print(f"dataset error: {exc}", file=sys.stderr)
        return 1
    summary = split_summary(everything)
    print(f"{len(cases)} {args.split} cases (of {len(everything)}); split: {summary}")
    if args.validate_only:
        return 0
    if args.batch:
        print("--batch (Message Batches API) is not implemented yet (TODO).", file=sys.stderr)
        return EXIT_REFUSED
    if args.runs < 1 or args.concurrency < 1:
        print("--runs and --concurrency must be at least 1", file=sys.stderr)
        return 1

    settings = settings or Settings()
    judge_model: str = args.judge_model or settings.eval_judge_model
    judge_prompt: JudgePrompt | None = None
    uncalibrated: str | None = None
    if args.judge:
        try:
            judge_prompt = load_judge_prompt(args.judge_prompt_version)
        except JudgePromptError as exc:
            print(f"configuration error: {exc}", file=sys.stderr)
            return 1
        try:
            require_calibration(judge_prompt, judge_model, args.judge_effort, args.calibration_dir)
        except JudgeNotCalibrated as exc:
            uncalibrated = str(exc)
            if not args.dry_run:
                print(f"--judge refused: {exc}. No model call was made.", file=sys.stderr)
                return EXIT_JUDGE_BLOCKED
    try:
        configs = _resolve_configs(args, settings)
        prices = load_prices()
        cache = None if args.no_cache else ResultCache(args.cache_dir)
        prints = {c.name: config_fingerprint(c, settings.content_dir) for c in configs}
        items = []
        for c in configs:
            misses = sum(
                1
                for i in range(args.runs)
                for case in cases
                if cache is None or not cache.has(case, i, prints[c.name])
            )
            items.append((c, misses, table_token_estimate(c, cases, settings.content_dir)))
        estimate = estimate_run(items, prices)
        if judge_prompt is not None:
            judge_est = _judge_estimate(
                cases,
                judge_prompt,
                judge_model,
                args.judge_effort,
                len(cases) * args.runs * len(configs),
                prices,
            )
            estimate = CostEstimate(estimate.lines + judge_est.lines, estimate.prices_retrieved_on)
    except (PromptLoadError, PriceError, KeyError, ValueError) as exc:
        print(f"configuration error: {exc!r}", file=sys.stderr)
        return 1
    print(format_estimate(estimate, args.runs, len(cases)))
    if args.dry_run:
        if uncalibrated is not None:
            print(
                f"Warning: a real run with --judge would stop (exit {EXIT_JUDGE_BLOCKED}): "
                f"{uncalibrated}",
                file=sys.stderr,
            )
        print("Dry run: no model call was made.")
        return 0

    client: ModelClient | None = None
    if estimate.calls > 0:
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

    ctx = load_context(settings.content_dir)
    runs: list[ConfigRun] = []
    for c in configs:
        recorder = CallRecorder()
        coach = build_eval_coach(c, settings, client, metrics_sink=recorder.sink)
        measured = asyncio.run(
            run_measured(
                coach,
                cases,
                ctx,
                runs=args.runs,
                concurrency=args.concurrency,
                recorder=recorder,
                cache=cache,
                fingerprint=prints[c.name],
            )
        )
        metrics: ConfigMetrics = compute_metrics(
            c,
            measured,
            prices,
            concurrency=args.concurrency,
            timeout_budget_s=TIMEOUT_BUDGET_SECONDS,
        )
        quality: QualityResult | None = None
        if judge_prompt is not None:
            judge = Judge(client, prompt=judge_prompt, model=judge_model, effort=args.judge_effort)
            try:
                quality = asyncio.run(
                    judge_measured(
                        measured,
                        judge,
                        concurrency=args.concurrency,
                        calibration_dir=args.calibration_dir,
                    )
                )
            except JudgeNotCalibrated as exc:  # checked above; defence in depth
                print(f"--judge refused: {exc}", file=sys.stderr)
                return EXIT_JUDGE_BLOCKED
            metrics = with_judged_quality(metrics, quality)
        runs.append(
            ConfigRun(metrics, measured, fingerprint_parts(c, settings.content_dir), quality)
        )

    selection: SelectionResult | None = None
    try:
        selection = select([r.metrics for r in runs])
    except SelectionError as exc:
        print(f"Selection not applied: {exc}", file=sys.stderr)
    json_path, md_path = write_report(
        args.stage,
        runs,
        selection,
        prices,
        dataset_split=args.split,
        on=today,
        out_dir=args.report_dir,
    )
    print(f"Report: {json_path} and {md_path}")
    if selection is not None:
        print(f"Winner: {selection.winner or 'none (no configuration passed the hard gates)'}")
        for note in selection.notes:
            print(f"Note: {note}")
        return 0 if selection.winner else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
