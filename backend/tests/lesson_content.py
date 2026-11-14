"""A temp copy of `content/` with exactly two built lessons: `m1_l1` and a fixture `m1_l2` (no
variants). The real `m1_l2` is replaced and `m1_l3` to `m1_l5` are removed (marked unbuilt) so
these tests do not depend on them."""

import copy
import json
import shutil
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
UNBUILT_REAL_LESSONS = frozenset({"m1_l3", "m1_l4", "m1_l5"})


def _drop_variants(lesson: dict[str, Any]) -> dict[str, Any]:
    """m1_l1 without its setup question: every by-variant block keeps the `in_person` entry."""
    lesson["id"] = "m1_l2"
    lesson["title"] = "Fixture lesson for {recipient}"
    lesson["screens"] = [s for s in lesson["screens"] if s["type"] != "setup_question"]
    for screen in lesson["screens"]:
        _flatten(screen)
    day2 = lesson["day2"]
    for block in (day2["checkIn"], day2["practiceRound"]):
        _flatten(block)
    return lesson


def _flatten(node: dict[str, Any]) -> None:
    """Replace `xByVariant`/`by_variant` dicts by `default` and clear the `*VariantMap`s."""
    for key in list(node):
        if key.endswith("VariantMap"):
            node[key] = {}
        elif key in ("byVariant", "answers", "bullets", "roundsByVariant") or key.endswith(
            "ByVariant"
        ):
            value = node[key]
            if isinstance(value, dict) and "in_person" in value:
                node[key] = {"default": value["in_person"]}
            elif isinstance(value, dict) and "default" not in value and key == "byVariant":
                node[key] = {"default": value.get("in_person", next(iter(value.values())))}
        elif isinstance(node[key], dict):
            _flatten(node[key])


def make_content_dir(target: Path) -> Path:
    """Copy `content/` to `target` and make `m1_l2` a built, variant-free lesson."""
    shutil.copytree(REPO / "content", target)
    rules_path = target / "plan-rules.json"
    rules = json.loads(rules_path.read_text())
    for module in rules["modules"]:
        for lesson in module["lessons"]:
            if lesson["id"] == "m1_l2":
                lesson["built"] = True
            elif lesson["id"] in UNBUILT_REAL_LESSONS:
                lesson["built"] = False  # the real ones are built; fixtures keep only l1 and l2
    rules_path.write_text(json.dumps(rules))
    for lesson_id in UNBUILT_REAL_LESSONS:
        (target / "lessons" / f"{lesson_id}.json").unlink(missing_ok=True)
    source = json.loads((target / "lessons" / "m1_l1.json").read_text())
    fixture = _drop_variants(copy.deepcopy(source))
    (target / "lessons" / "m1_l2.json").write_text(json.dumps(fixture))
    return target
