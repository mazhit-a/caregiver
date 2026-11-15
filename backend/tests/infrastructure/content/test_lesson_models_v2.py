"""Lesson models v2 (new screen types, normalized arrays) and the lesson validation layer."""

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from app.infrastructure.content.lesson_validation import validate_lesson
from app.infrastructure.content.loader import ContentLoadError, load_content
from app.infrastructure.content.schemas import (
    BuilderScreen,
    ContentScreen,
    IntroScreen,
    LessonFile,
    QuizScreen,
    ResetScreen,
    ScenarioScreen,
    SetupScreen,
)

REPO = Path(__file__).resolve().parents[3].parent
REAL = REPO / "content"
PACKAGE_LESSON = REPO / "context" / "design" / "content-package" / "lessons" / "m1_l1.json"
VARIANTS = {"a": "A", "b": "B"}

SCREENS: dict[str, dict[str, Any]] = {
    "intro": {
        "id": "intro",
        "type": "intro",
        "minutes": 2,
        "title": "T",
        "body": "B",
        "bullets": ["x"],
        "image": "ollie-welcome",
        "sec": 30,
    },
    "setup": {
        "id": "setup",
        "type": "setup",
        "title": "T",
        "body": "B",
        "options": [["a", "A"], ["b", "B"]],
        "sec": 10,
    },
    "scenario": {
        "id": "scenario",
        "type": "scenario",
        "title": "T",
        "note": "N",
        "setupByVariant": {"a": "s", "b": "s"},
        "lineByVariant": {"a": "l", "b": "l"},
        "optionsByVariant": {
            "a": [["one", "best", "f"], ["two", "try_again", "f"]],
            "b": [["one", "okay", "f"]],
        },
        "sec": 20,
    },
    "content": {
        "id": "c1",
        "type": "content",
        "part": "P",
        "title": "T",
        "bodyByVariant": {"a": ["x"], "b": ["y"]},
        "items": [["t", "x"]],
        "steps": [["1", "t", "x"]],
        "dodont": {"do": ["d"], "dont": ["n"]},
        "examples": [["e", "why"]],
        "example": ["l1", "l2"],
        "keyIdea": "k",
        "tip": "t",
        "image": "ollie-explaining",
        "sec": 10,
    },
    "quiz": {
        "id": "q1",
        "type": "quiz",
        "title": "T",
        "options": [["a", False, "f"], ["b", True, "f"]],
        "sec": 10,
    },
    "builder": {
        "id": "builder",
        "type": "builder",
        "title": "T",
        "body": "B",
        "groups": [["G1", [["a", True], ["b", False]]], ["G2", [["c", False], ["d", True]]]],
        "sec": 10,
    },
    "reset": {
        "id": "you",
        "type": "reset",
        "title": "T",
        "body": "B",
        "question": "Q",
        "options": ["breathe", ["pause", "take a pause"]],
        "sec": 10,
    },
}
SCREEN_ORDER = ("intro", "setup", "scenario", "content", "quiz", "builder", "reset")


def _lesson(**changes: Any) -> dict[str, Any]:
    screens = [copy.deepcopy(SCREENS[key]) for key in SCREEN_ORDER]
    screens.append(
        {
            "id": "plan",
            "type": "plan",
            "title": "T",
            "ifThen": {
                "cueByVariant": {"a": "c", "b": "c"},
                "cueVariantMap": {},
                "responseLabel": "r",
                "responseDefault": "d",
                "responseEditable": True,
                "resetLabel": "l",
                "resetFrom": "you",
            },
            "doNow": {
                "title": "t",
                "byVariant": {
                    "a": {"text": "t", "action": "a", "button": "b"},
                    "b": {"text": "t", "action": "a", "button": "b"},
                },
            },
            "remindButton": "r",
            "doneButton": "d",
            "noteTemplate": {"title": "t", "example": "e"},
            "sec": 10,
        }
    )
    screens.append(
        {
            "id": "wrap",
            "type": "wrap",
            "title": "Done",
            "learned": ["one"],
            "skillLine": "s",
            "phraseLine": "p",
            "patternLine": "p",
            "tomorrowLine": "t",
            "nextLine": "n",
            "sec": 10,
        }
    )
    lesson: dict[str, Any] = {
        "id": "m1_l9",
        "version": 1,
        "moduleId": "m1",
        "title": "T",
        "minutes": 2,
        "skill": "s",
        "skillLabel": "S",
        "pattern": {"name": "n", "steps": []},
        "screens": screens,
        "fallbackScenarios": [],
        "day2": json.loads((REAL / "lessons" / "m1_l1.json").read_text())["day2"],
        "recapForNextLesson": {"text": "t", "ifCheckInHelped": "h"},
    }
    lesson.update(changes)
    return lesson


def _screen(lesson: dict[str, Any], screen_id: str) -> dict[str, Any]:
    return next(s for s in lesson["screens"] if s["id"] == screen_id)


def _problems(lesson: dict[str, Any]) -> list[tuple[str, str]]:
    return validate_lesson(LessonFile.model_validate(lesson))


def test_each_new_screen_type_loads_and_arrays_are_normalized() -> None:
    lesson = LessonFile.model_validate(_lesson())
    by_type = {type(s): s for s in lesson.screens}
    intro = by_type[IntroScreen]
    assert intro.minutes == 2 and intro.image == "ollie-welcome" and intro.sec == 30
    setup = by_type[SetupScreen]
    assert [(o.id, o.label) for o in setup.options] == [("a", "A"), ("b", "B")]
    assert lesson.variant_ids() == ["a", "b"]
    scenario = by_type[ScenarioScreen]
    assert [o.id for o in scenario.options_by_variant["a"]] == ["a1", "a2"]
    assert scenario.options_by_variant["a"][1].verdict == "try_again"
    content = by_type[ContentScreen]
    assert content.steps is not None and content.steps[0].n == "1"
    assert content.dodont is not None and content.dodont.dont == ["n"]
    assert content.example is not None and content.example.line2 == "l2"
    assert content.examples is not None and content.examples[0].why == "why"
    assert content.part == "P"
    quiz = by_type[QuizScreen]
    assert [(o.id, o.correct) for o in quiz.options] == [("o1", False), ("o2", True)]
    builder = by_type[BuilderScreen]
    assert [g.id for g in builder.groups] == ["g1", "g2"]
    assert builder.groups[1].options[1].id == "o2" and builder.groups[1].options[1].correct
    reset = by_type[ResetScreen]
    assert [(o.id, o.label, o.plan_text) for o in reset.options] == [
        ("r1", "breathe", None),
        ("r2", "pause", "take a pause"),
    ]
    assert _problems(_lesson()) == []


def test_a_wrong_array_length_is_rejected_with_the_field_path() -> None:
    lesson = _lesson()
    _screen(lesson, "q1")["options"][0] = ["only text"]
    with pytest.raises(ValueError, match=r"screens\.4\.quiz\.options\.0"):
        LessonFile.model_validate(lesson)


def test_unknown_screen_fields_still_fail() -> None:
    lesson = _lesson()
    _screen(lesson, "q1")["surprise"] = 1
    with pytest.raises(ValueError, match="surprise"):
        LessonFile.model_validate(lesson)


def test_old_shape_scenarios_normalize_to_the_canonical_model() -> None:
    lesson = load_content(REAL).lessons["m1_l2"]  # lessons 2 to 5 keep the old shape
    scenario = next(s for s in lesson.screens if isinstance(s, ScenarioScreen))
    assert scenario.by_variant is not None and scenario.answers is not None  # old shape kept
    assert set(scenario.setup_by_variant) == set(scenario.by_variant)
    assert scenario.line_by_variant["default"] == scenario.by_variant["default"].line
    assert scenario.options_by_variant["default"][0].id == scenario.answers["default"][0].id
    assert scenario.options_variant_map == scenario.answers_variant_map


def test_the_five_real_lessons_load() -> None:
    assert sorted(load_content(REAL).lessons) == ["m1_l1", "m1_l2", "m1_l3", "m1_l4", "m1_l5"]


# ------------------------------------------------------------------ validation rules


def test_duplicate_screen_ids_are_reported() -> None:
    lesson = _lesson()
    _screen(lesson, "q1")["id"] = "you"
    assert ("screens.6.id", "duplicate screen id 'you'") in _problems(lesson)


def test_reset_from_must_name_a_screen() -> None:
    lesson = _lesson()
    _screen(lesson, "plan")["ifThen"]["resetFrom"] = "nope"
    assert any(p == "screens.7.ifThen.resetFrom" for p, _ in _problems(lesson))


def test_roleplay_fallback_ids_must_exist() -> None:
    lesson = LessonFile.model_validate(
        load_content(REAL).lessons["m1_l2"].model_dump(by_alias=True)
    )
    assert validate_lesson(lesson) == []
    data = lesson.model_dump(by_alias=True, mode="json", exclude_none=True)
    roleplay = next(s for s in data["screens"] if s["type"] == "roleplay")
    roleplay["fallbackScenarios"].append("fb_missing")
    problems = validate_lesson(LessonFile.model_validate(data))
    assert any("fallbackScenarios" in path and "fb_missing" in msg for path, msg in problems)


def test_at_most_one_setup_and_it_comes_first() -> None:
    lesson = _lesson()
    lesson["screens"].insert(5, copy.deepcopy(SCREENS["setup"]) | {"id": "setup2"})
    assert ("screens.5", "a lesson has at most one setup screen") in _problems(lesson)
    late = _lesson()
    late["screens"].insert(0, late["screens"].pop(2))  # scenario before the setup
    assert any(p == "screens.0" and "after the setup" in m for p, m in _problems(late))


def test_every_by_variant_block_must_resolve_for_every_variant() -> None:
    lesson = _lesson()
    del _screen(lesson, "scenario")["optionsByVariant"]["b"]
    del _screen(lesson, "c1")["bodyByVariant"]["b"]
    problems = dict(_problems(lesson))
    assert "variant 'b'" in problems["screens.2.optionsByVariant"]
    assert "variant 'b'" in problems["screens.3.bodyByVariant"]
    lesson = _lesson()
    _screen(lesson, "c1")["bodyVariantMap"] = {"b": "a"}
    del _screen(lesson, "c1")["bodyByVariant"]["b"]
    assert _problems(lesson) == []  # a map entry covers the variant


def test_builder_group_needs_exactly_one_correct_option() -> None:
    lesson = _lesson()
    _screen(lesson, "builder")["groups"][1][1][0][1] = True
    assert any(p == "screens.5.groups.1.options" for p, _ in _problems(lesson))


def test_quiz_needs_exactly_one_correct_option() -> None:
    lesson = _lesson()
    _screen(lesson, "q1")["options"][0][1] = True
    assert any(p == "screens.4.options" for p, _ in _problems(lesson))
    none_correct = _lesson()
    _screen(none_correct, "q1")["options"][1][1] = False
    assert any(p == "screens.4.options" for p, _ in _problems(none_correct))


def test_scenario_and_fallback_verdicts_use_the_shared_vocabulary() -> None:
    lesson = _lesson()
    _screen(lesson, "scenario")["optionsByVariant"]["a"][1][1] = "try"
    path = "screens.2.optionsByVariant.a.1.verdict"
    assert any(p == path and "try_again" in m for p, m in _problems(lesson))
    lesson = _lesson(
        fallbackScenarios=[
            {
                "id": "fb1",
                "setup": "s",
                "line": "l",
                "answers": [{"text": "t", "verdict": "bad", "feedback": "f"}],
            }
        ]
    )
    assert any(p == "fallbackScenarios.0.answers.0.verdict" for p, _ in _problems(lesson))


def test_intro_minutes_and_the_sum_of_seconds_must_match_the_lesson() -> None:
    lesson = _lesson(minutes=4)
    paths = [p for p, _ in _problems(lesson)]
    assert "screens.0.minutes" in paths and "minutes" in paths
    assert [p for p, _ in _problems(_lesson())] == []  # 120 s = 2 minutes


# ------------------------------------------------------------------ the loader and the package file


def _content_with(tmp_path: Path, lesson: dict[str, Any]) -> Path:
    target = tmp_path / "content"
    shutil.copytree(REAL, target)
    (target / "lessons" / "m1_l1.json").write_text(json.dumps(lesson))
    return target


def test_the_loader_names_the_file_and_the_field_path(tmp_path: Path) -> None:
    lesson = json.loads((REAL / "lessons" / "m1_l1.json").read_text())
    lesson["screens"][0]["id"] = lesson["screens"][1]["id"]
    with pytest.raises(ContentLoadError, match=r"lessons/m1_l1\.json: screens\.1\.id: duplicate"):
        load_content(_content_with(tmp_path, lesson))


def test_a_valid_new_shape_lesson_passes_the_loader(tmp_path: Path) -> None:
    lesson = _lesson(id="m1_l1", moduleId="m1")
    assert load_content(_content_with(tmp_path, lesson)).lessons["m1_l1"].variant_ids() == [
        "a",
        "b",
    ]


def test_the_unpatched_package_lesson_loads_but_fails_validation_with_the_known_gaps(
    tmp_path: Path,
) -> None:
    """Documents the gap list of PLAN-04 1.6 (items 1 to 4): P11 patches the content."""
    target = tmp_path / "content"
    shutil.copytree(REAL, target)
    shutil.copy(PACKAGE_LESSON, target / "lessons" / "m1_l1.json")
    with pytest.raises(ContentLoadError) as info:
        load_content(target)
    message = str(info.value)
    assert "screens.22.ifThen.resetFrom" in message  # stale "s6_fifth_time"
    assert "screens.2.optionsByVariant" in message  # no entry for both and not_yet
    assert "screens.16.bodyByVariant" in message  # tools has no entry for both
    assert "'try' is not one of best, okay, try_again" in message
