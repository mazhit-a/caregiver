"""Human labels for judge calibration: file format, validator and a draft generator.

`evals/datasets/human_labels.jsonl` (the REAL file) is produced by a person, never by code. One
JSON line per labelled output (camelCase), see `evals/LABELING.md`:

    {"id": "h01", "labeler": "<name>", "label": "Mom", "parentLine": "...", "parentMood": "worried",
     "previousTurns": [{"parent": "...", "caregiver": "..."}], "caregiverReply": "...",
     "coachOutput": {"score": 2, "tip": "...", "betterPhrase": "...", "parentReaction": "...",
                     "parentMood": "calmer"},
     "human": {"betterPhrase": 4, "tip": 5, "parentReaction": 3}, "note": "optional"}

The shipped `human_labels.template.jsonl` holds EXAMPLE rows marked `"template": true`; the
validator refuses such rows in the real file, so a template cannot pass for labels.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from evals.graders.judge import BETTER_PHRASE, PARENT_REACTION, RUBRIC_ITEMS, TIP, JudgeItem

DATASETS_DIR: Final = Path(__file__).resolve().parent / "datasets"
HUMAN_LABELS_PATH: Final = DATASETS_DIR / "human_labels.jsonl"
TEMPLATE_PATH: Final = DATASETS_DIR / "human_labels.template.jsonl"
DRAFT_PATH: Final = DATASETS_DIR / "human_labels.draft.jsonl"
MIN_LABELS: Final = 20
# A judge that always says 4 would "agree" with a file of only good outputs: the file must contain
# weak outputs for every rubric item.
MIN_WEAK_PER_ITEM: Final = 3
WEAK_AT_OR_BELOW: Final = 2


class LabelError(Exception):
    """The label file is malformed, a template, or too small to calibrate on."""


class _Strict(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


class PreviousTurnLabel(_Strict):
    parent: str
    caregiver: str


class CoachOutputLabel(_Strict):
    score: int = Field(ge=0, le=3)
    tip: str = Field(min_length=1)
    better_phrase: str = Field(min_length=1)
    parent_reaction: str = Field(min_length=1)
    parent_mood: str = Field(min_length=1)


class HumanScores(_Strict):
    better_phrase: int = Field(ge=1, le=5)
    tip: int = Field(ge=1, le=5)
    parent_reaction: int = Field(ge=1, le=5)


class HumanLabel(_Strict):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_\-.]+$")
    template: bool = False
    labeler: str = Field(min_length=1)
    label: str = "Mom"
    parent_line: str = Field(min_length=1)
    parent_mood: str = Field(min_length=1)
    previous_turns: tuple[PreviousTurnLabel, ...] = ()
    caregiver_reply: str = Field(min_length=1)
    coach_output: CoachOutputLabel
    human: HumanScores
    note: str = ""

    def to_item(self) -> JudgeItem:
        o = self.coach_output
        return JudgeItem(
            label=self.label,
            parent_line=self.parent_line,
            parent_mood=self.parent_mood,
            caregiver_reply=self.caregiver_reply,
            tip=o.tip,
            better_phrase=o.better_phrase,
            parent_reaction=o.parent_reaction,
            coach_parent_mood=o.parent_mood,
            coach_score=o.score,
            previous_turns=tuple((t.parent, t.caregiver) for t in self.previous_turns),
        )

    def human_scores(self) -> dict[str, int]:
        return {
            BETTER_PHRASE: self.human.better_phrase,
            TIP: self.human.tip,
            PARENT_REACTION: self.human.parent_reaction,
        }


def parse_labels(text: str, *, source: str = "labels") -> list[HumanLabel]:
    """Parse and validate (no minimum): used for the template and for tests."""
    rows: list[HumanLabel] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(HumanLabel.model_validate(json.loads(line)))
        except (ValueError, ValidationError) as exc:
            raise LabelError(f"{source}:{number}: {exc}") from None
    ids = [r.id for r in rows]
    if len(set(ids)) != len(ids):
        raise LabelError(f"{source}: duplicate ids")
    return rows


def validate_labels(rows: Sequence[HumanLabel], *, min_labels: int = MIN_LABELS) -> None:
    """The rules for a REAL calibration file."""
    templates = [r.id for r in rows if r.template]
    if templates:
        raise LabelError(f"template rows are not labels: {templates}")
    if len(rows) < min_labels:
        raise LabelError(f"need at least {min_labels} human-labelled outputs, got {len(rows)}")
    for item in RUBRIC_ITEMS:
        weak = sum(1 for r in rows if r.human_scores()[item] <= WEAK_AT_OR_BELOW)
        if weak < MIN_WEAK_PER_ITEM:
            raise LabelError(
                f"item {item}: need at least {MIN_WEAK_PER_ITEM} labels of "
                f"{WEAK_AT_OR_BELOW} or lower (a file of only good outputs cannot test a judge)"
            )


def load_labels(
    path: Path = HUMAN_LABELS_PATH, *, min_labels: int = MIN_LABELS
) -> list[HumanLabel]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LabelError(f"cannot read {path}: {exc.strerror}") from None
    rows = parse_labels(text, source=path.name)
    validate_labels(rows, min_labels=min_labels)
    return rows


# ------------------------------------------------------------------ draft rows (user task aid)


def draft_rows_from_cache(config_names: Sequence[str], prompt_version: str) -> list[str]:
    """Unlabelled rows (`"human": null`) from verdicts already in the result cache: no model call.
    Run `python -m evals.run` first so the cache has outputs. Only coached, unflagged outcomes."""
    from app.infrastructure.config import Settings
    from evals.cache import ResultCache, config_fingerprint
    from evals.client import production_config
    from evals.configs import candidate
    from evals.dataset import Split, load_split
    from evals.runner import grade_attempt, load_context

    settings = Settings()
    ctx = load_context(settings.content_dir)
    cache = ResultCache()
    lines: list[str] = []
    for name in config_names:
        config = (
            production_config(settings) if name == "production" else candidate(name, prompt_version)
        )
        fp = config_fingerprint(config, settings.content_dir)
        for case in load_split(Split.DEV):
            hit = cache.get(case, 0, fp)
            if hit is None:
                continue
            outcome = grade_attempt(case, ctx, 0, hit.verdict, None).outcome
            if outcome is None or outcome.flags or outcome.kind.value != "coached":
                continue
            lines.append(
                json.dumps(
                    {
                        "id": f"{name}-{case.id}",
                        "labeler": "",
                        "label": case.label,
                        "parentLine": case.parent_line,
                        "parentMood": case.parent_mood,
                        "previousTurns": [
                            {"parent": t.parent, "caregiver": t.caregiver}
                            for t in case.previous_turns
                        ],
                        "caregiverReply": case.caregiver_reply,
                        "coachOutput": {
                            "score": outcome.score,
                            "tip": outcome.tip,
                            "betterPhrase": outcome.better_phrase,
                            "parentReaction": outcome.parent_reaction,
                            "parentMood": outcome.parent_mood,
                        },
                        "human": None,
                        "note": "",
                    },
                    ensure_ascii=False,
                )
            )
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.labels", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    val = sub.add_parser("validate", help="validate a label file (default: the real one)")
    val.add_argument("path", nargs="?", type=Path, default=HUMAN_LABELS_PATH)
    draft = sub.add_parser(
        "draft", help="write unlabelled rows from cached outputs (no model call)"
    )
    draft.add_argument("--config", nargs="+", default=["production"])
    draft.add_argument("--prompt-version", default="1")
    draft.add_argument("--out", type=Path, default=DRAFT_PATH)
    args = parser.parse_args(argv)
    if args.command == "validate":
        try:
            rows = load_labels(args.path)
        except LabelError as exc:
            print(f"label file invalid: {exc}", file=sys.stderr)
            return 1
        print(f"OK: {len(rows)} labels from {len(set(r.labeler for r in rows))} labeler(s)")
        return 0
    lines = draft_rows_from_cache(args.config, args.prompt_version)
    args.out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"{len(lines)} unlabelled rows written to {args.out}; fill in `human` and `labeler`.")
    return 0 if lines else 1


if __name__ == "__main__":
    raise SystemExit(main())
