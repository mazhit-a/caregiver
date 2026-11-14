"""Eval runner CLI. `uv run python -m evals.run --help` works offline.

A run that would call a real model first prints a cost estimate and needs confirmation (see
`evals/cost.py`). `--dry-run` prints the estimate and exits. Results are cached, so only what
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
from evals.client import CoachConfig, ModelClient, build_eval_coach, production_config, real_client
from evals.configs import STAGES, candidate, candidate_names
from evals.cost import confirm_run, estimate_run, format_estimate, table_token_estimate
from evals.dataset import (
    GOLDEN_PATH,
    DatasetError,
    Split,
    load_all_acknowledging_test,
    load_split,
    split_summary,
)
from evals.metrics import ConfigMetrics, compute_metrics, load_prices
from evals.report import DEFAULT_REPORT_DIR, ConfigRun, write_report
from evals.rule import CONSISTENCY_RUNS, TIMEOUT_BUDGET_SECONDS
from evals.runner import CallRecorder, load_context, run_measured
from evals.selection import SelectionError, SelectionResult, select

EXIT_REFUSED = 2


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
    except (PromptLoadError, KeyError, ValueError) as exc:
        print(f"configuration error: {exc!r}", file=sys.stderr)
        return 1
    print(format_estimate(estimate, args.runs, len(cases)))
    if args.dry_run:
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
        runs.append(ConfigRun(metrics, measured, fingerprint_parts(c, settings.content_dir)))

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
