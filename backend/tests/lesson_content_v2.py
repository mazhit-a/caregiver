"""A temp copy of `content/` whose `m1_l1` uses the new screen types (P9 tests).

The pattern, role-play, plan and wrap screens, `day2` and recap come from the real lesson; the
setup, scenario, teaching, quiz, builder and reset screens are small hand-written ones that
exercise every by-variant block, so the tests do not depend on the content swap (P11).
"""

import json
from pathlib import Path
from typing import Any

from tests.lesson_content import make_content_dir

VARIANTS = ("in_person", "phone", "both", "not_yet")

V2_SCREENS: list[dict[str, Any]] = [
    {
        "id": "intro",
        "type": "intro",
        "part": "Start",
        "minutes": 9,
        "title": "Talking with {recipient}",
        "body": "A short lesson about {possessive} repeated questions.",
        "bullets": ["One idea", "One phrase"],
        "image": "ollie-welcome",
    },
    {
        "id": "setup",
        "type": "setup",
        "title": "How do you talk?",
        "body": "Pick one.",
        "options": [
            ["in_person", "In person"],
            ["phone", "By phone"],
            ["both", "Both"],
            ["not_yet", "Not yet"],
        ],
    },
    {
        "id": "scenario",
        "type": "scenario",
        "part": "Moment",
        "title": "A repeated question",
        "note": "Pick what feels closest.",
        "setupByVariant": {"in_person": "At home with {recipient}.", "phone": "On a call."},
        "setupVariantMap": {"both": "in_person", "not_yet": "in_person"},
        "lineByVariant": {"in_person": "Where is my bag?", "phone": "Who is this?"},
        "optionsByVariant": {
            "in_person": [
                ["Say it is in the hall.", "best", "Good instinct."],
                ["Say you told {object} already.", "try_again", "Very common."],
            ],
            "phone": [["Say who you are.", "okay", "Noted."]],
        },
        "optionsVariantMap": {"both": "in_person", "not_yet": "in_person"},
    },
    {
        "id": "idea",
        "type": "content",
        "part": "Idea",
        "title": "Notice first",
        "bodyByVariant": {
            "in_person": ["Look at {recipient}."],
            "phone": ["Listen to {recipient}."],
        },
        "bodyVariantMap": {"both": "in_person", "not_yet": "in_person"},
        "items": [["One", "Notice"]],
        "keyIdea": "Feelings first.",
        "tip": "Slow down.",
    },
    {
        "id": "check",
        "type": "quiz",
        "title": "Quick check",
        "options": [
            ["Argue about facts", False, "Not quite."],
            ["Name the feeling", True, "That's right."],
        ],
    },
    {
        "id": "build",
        "type": "builder",
        "title": "Build a reply",
        "body": "Pick one from each.",
        "groups": [
            ["Notice", [["You seem worried.", True], ["You asked already.", False]]],
            ["Reassure", [["I am here.", True], ["Stop asking.", False]]],
        ],
    },
    {
        "id": "you",
        "type": "reset",
        "title": "Your reset",
        "body": "What helps you?",
        "question": "Before you answer, I will:",
        "options": [["One slow breath", "take one slow breath"], "Step away"],
    },
]


def v2_lesson(source: dict[str, Any]) -> dict[str, Any]:
    old = {s["id"]: s for s in source["screens"]}
    plan = json.loads(json.dumps(old["plan"]))
    plan["ifThen"]["resetFrom"] = "you"
    lesson = json.loads(json.dumps(source))
    lesson["screens"] = [*V2_SCREENS, old["practice"], plan, _wrap(old["wrap"])]
    return lesson


def _wrap(wrap: dict[str, Any]) -> dict[str, Any]:
    return {**wrap, "title": "Well done", "learned": ["Notice the feeling"]}


def make_v2_content_dir(target: Path) -> Path:
    make_content_dir(target)
    path = target / "lessons" / "m1_l1.json"
    path.write_text(json.dumps(v2_lesson(json.loads(path.read_text()))))
    return target
