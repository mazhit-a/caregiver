"""Eval runner CLI (skeleton). `uv run python -m evals.run --help` works offline.

This increment only loads and validates the dataset. Real model runs need the cost estimate and
the confirmation prompt that arrive with the metrics and selection increment, so a run that would
call the model is refused here.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from evals.dataset import (
    GOLDEN_PATH,
    DatasetError,
    Split,
    load_all_acknowledging_test,
    load_split,
    split_summary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evals.run",
        description=(
            "Role-play eval runner: runs cases through the production coach and domain rules and "
            "grades them with code-based graders. REAL model calls cost money."
        ),
    )
    parser.add_argument("--config", default="production", help="harness configuration name")
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


def main(argv: Sequence[str] | None = None) -> int:
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
    print(
        "Real model runs are not enabled yet: the cost estimate and confirmation come with the "
        "metrics increment. Use --validate-only.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
