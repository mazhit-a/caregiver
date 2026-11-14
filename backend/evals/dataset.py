"""Dataset files, the package conversion and the dev/test split.

Split: deterministic by case id (sha256 of seed + id), so a case never changes side when other
cases are added, and the test split stays held out. Loaders take the split explicitly; the only way
to get both is `load_all_acknowledging_test`, whose name says what it does.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from pydantic import ValidationError

from evals.case import EvalCase, parse_case

DATASETS_DIR: Final = Path(__file__).resolve().parent / "datasets"
GOLDEN_PATH: Final = DATASETS_DIR / "golden.jsonl"
PACKAGE_EVALS_PATH: Final = (
    Path(__file__).resolve().parents[2] / "content" / "evals" / "roleplay-evals.json"
)

SPLIT_SEED: Final = "pcn-eval-v2"
TEST_SHARE_PERCENT: Final = 30


class Split(StrEnum):
    DEV = "dev"
    TEST = "test"


class DatasetError(Exception):
    """A dataset file is invalid, or a loader was used in a way that would mix the splits."""


def split_of(case_id: str) -> Split:
    digest = hashlib.sha256(f"{SPLIT_SEED}:{case_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big") % 100
    return Split.TEST if bucket < TEST_SHARE_PERCENT else Split.DEV


def read_jsonl(path: Path) -> list[EvalCase]:
    """Parse and validate every line; ids must be unique. Errors name the file and line."""
    cases: list[EvalCase] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = parse_case(json.loads(line))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise DatasetError(f"{path.name}:{number}: invalid case ({exc})") from exc
        if case.id in seen:
            raise DatasetError(f"{path.name}:{number}: duplicate case id {case.id!r}")
        seen.add(case.id)
        cases.append(case)
    return cases


def _read_all(paths: Sequence[Path]) -> list[EvalCase]:
    cases: list[EvalCase] = []
    seen: dict[str, Path] = {}
    for path in paths:
        for case in read_jsonl(path):
            if case.id in seen:
                raise DatasetError(
                    f"case id {case.id!r} is in both {seen[case.id].name} and {path.name}"
                )
            seen[case.id] = path
            cases.append(case)
    return cases


def load_split(split: Split, paths: Sequence[Path] = (GOLDEN_PATH,)) -> list[EvalCase]:
    """The cases of ONE split. `split` is required: there is no default that mixes them."""
    if not isinstance(split, Split):
        raise DatasetError("split must be Split.DEV or Split.TEST")
    return [c for c in _read_all(paths) if split_of(c.id) is split]


def load_all_acknowledging_test(
    paths: Sequence[Path] = (GOLDEN_PATH,), *, i_know_this_uses_the_test_set: bool = False
) -> list[EvalCase]:
    """Every case, dev and test together: for validation and tooling, never for tuning."""
    if not i_know_this_uses_the_test_set:
        raise DatasetError("loading dev and test together needs i_know_this_uses_the_test_set=True")
    return _read_all(paths)


def assert_disjoint(dev: Iterable[EvalCase], test: Iterable[EvalCase]) -> None:
    both = {c.id for c in dev} & {c.id for c in test}
    if both:
        raise DatasetError(f"ids in both dev and test: {sorted(both)}")


def split_summary(cases: Iterable[EvalCase]) -> dict[str, dict[str, int]]:
    """Per split, the number of cases per stratum (flag kind or `scored`)."""
    summary: dict[str, Counter[str]] = {s.value: Counter() for s in Split}
    for case in cases:
        summary[split_of(case.id).value][case.stratum] += 1
    return {k: dict(sorted(v.items())) for k, v in summary.items()}


# ------------------------------------------------------------------ package conversion


def package_to_cases(raw: dict[str, Any]) -> list[EvalCase]:
    """`content/evals/roleplay-evals.json` -> cases tagged `source: package` (defaults merged)."""
    defaults: dict[str, Any] = raw.get("defaults", {})
    cases: list[EvalCase] = []
    for item in raw["cases"]:
        merged: dict[str, Any] = {**defaults, **item, "source": "package"}
        merged.pop("expect", None)
        merged["expect"] = item["expect"]
        cases.append(parse_case(merged))
    return cases


def convert_package(source: Path = PACKAGE_EVALS_PATH, target: Path = GOLDEN_PATH) -> int:
    """Write the package cases to JSONL (keeps any other cases already in `target`)."""
    package = package_to_cases(json.loads(source.read_text(encoding="utf-8")))
    others = [c for c in read_jsonl(target) if c.source != "package"] if target.exists() else []
    lines = [c.to_json_line() for c in [*package, *others]]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(package)
