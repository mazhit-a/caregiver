"""Renderers of the new screen types: variant applied, labels filled, nothing server-only."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.domain.lessons.errors import LessonContentError
from app.domain.lessons.screens import (
    RUNTIME_PLACEHOLDERS,
    RenderedLesson,
    render_lesson,
    visible_screens,
)
from app.infrastructure.content.provider import JsonContentProvider
from tests.lesson_content_v2 import VARIANTS, make_v2_content_dir

BLANKS = dict.fromkeys(RUNTIME_PLACEHOLDERS, "")
SERVER_ONLY_KEYS = {
    "correct",
    "verdict",
    "feedback",
    "planText",
    "savePhrase",
    "sec",
    "minutes",
    "bodyByVariant",
    "optionsByVariant",
    "setupByVariant",
    "lineByVariant",
    "setupVariantMap",
    "optionsVariantMap",
    "bodyVariantMap",
}


@pytest.fixture(scope="module")
def content(tmp_path_factory: pytest.TempPathFactory) -> JsonContentProvider:
    target = tmp_path_factory.mktemp("v2") / "content"
    return JsonContentProvider.from_directory(make_v2_content_dir(Path(target)))


def lesson(
    content: JsonContentProvider, variant: str | None, recipient: str = "mom"
) -> RenderedLesson:
    return render_lesson(content.render_lesson("m1_l1", recipient, variant, BLANKS), variant, True)


def screen(result: RenderedLesson, screen_id: str) -> dict[str, Any]:
    return next(s for s in result.screens if s["id"] == screen_id)


def keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in keys(v)}
    return set()


def test_before_the_variant_is_chosen_only_intro_and_setup_are_visible(
    content: JsonContentProvider,
) -> None:
    data = content.render_lesson("m1_l1", "mom", None, BLANKS)
    assert [s["id"] for s in visible_screens(data, None)] == ["intro", "setup"]
    assert len(visible_screens(data, "phone")) == len(data["screens"]) > 2
    assert [s["id"] for s in lesson(content, None).screens] == ["intro", "setup"]


def test_each_new_type_renders_the_learner_fields(content: JsonContentProvider) -> None:
    result = lesson(content, "in_person")
    intro = screen(result, "intro")
    assert intro["bullets"] == ["One idea", "One phrase"] and intro["image"] == "ollie-welcome"
    assert screen(result, "setup")["options"][0] == {"id": "in_person", "label": "In person"}
    quiz = screen(result, "check")
    assert quiz["options"] == [
        {"id": "o1", "text": "Argue about facts"},
        {"id": "o2", "text": "Name the feeling"},
    ]
    builder = screen(result, "build")
    assert [g["id"] for g in builder["groups"]] == ["g1", "g2"]
    assert builder["groups"][0]["options"][0] == {"id": "o1", "text": "You seem worried."}
    reset = screen(result, "you")
    assert reset["question"] and [o["id"] for o in reset["options"]] == ["r1", "r2"]
    wrap = screen(result, "wrap")
    assert wrap["title"] == "Well done" and wrap["learned"] == ["Notice the feeling"]


def test_content_screen_blocks_keep_the_authored_data(content: JsonContentProvider) -> None:
    idea = screen(lesson(content, "in_person"), "idea")
    assert idea["items"] == [{"title": "One", "text": "Notice"}]
    assert idea["keyIdea"] == "Feelings first." and idea["tip"] == "Slow down."


def test_part_is_copied_once_for_every_screen_type(content: JsonContentProvider) -> None:
    result = lesson(content, "phone")
    assert screen(result, "intro")["part"] == "Start"
    assert screen(result, "scenario")["part"] == "Moment"
    assert screen(result, "idea")["part"] == "Idea"
    assert "part" not in screen(result, "check")


@pytest.mark.parametrize("variant", VARIANTS)
def test_scenario_and_content_resolve_for_every_variant(
    content: JsonContentProvider, variant: str
) -> None:
    result = lesson(content, variant)
    scenario = screen(result, "scenario")
    assert scenario["setup"] and scenario["line"] and scenario["answers"]
    assert screen(result, "idea")["body"]
    # the screen path never depends on the variant
    assert [s["id"] for s in result.screens] == [s["id"] for s in lesson(content, "phone").screens]


def test_variant_selects_the_scenario_and_the_both_variants_map_to_in_person(
    content: JsonContentProvider,
) -> None:
    phone = screen(lesson(content, "phone"), "scenario")
    in_person = screen(lesson(content, "in_person"), "scenario")
    assert phone["line"] == "Who is this?" and len(phone["answers"]) == 1
    assert in_person["line"] == "Where is my bag?" and len(in_person["answers"]) == 2
    for variant in ("both", "not_yet"):
        assert screen(lesson(content, variant), "scenario") == in_person
    assert screen(lesson(content, "both"), "idea")["body"] == ["Look at Mom."]


@pytest.mark.parametrize("recipient", ["mom", "dad", "both", "in_law", "other"])
@pytest.mark.parametrize("variant", VARIANTS)
def test_no_placeholder_is_left_for_any_recipient_and_variant(
    content: JsonContentProvider, recipient: str, variant: str
) -> None:
    text = json.dumps(lesson(content, variant, recipient).screens)
    assert not re.search(r"\{\w+\}", text)


@pytest.mark.parametrize("variant", VARIANTS)
def test_no_server_only_key_reaches_any_rendered_screen(
    content: JsonContentProvider, variant: str
) -> None:
    assert keys(lesson(content, variant).screens) & SERVER_ONLY_KEYS == set()


def test_a_by_variant_block_the_variant_does_not_cover_is_a_content_error(
    content: JsonContentProvider,
) -> None:
    data = content.render_lesson("m1_l1", "mom", "phone", BLANKS)
    scenario = next(s for s in data["screens"] if s["id"] == "scenario")
    del scenario["lineByVariant"]["phone"]
    with pytest.raises(LessonContentError):
        render_lesson(data, "phone", True)


def test_content_screen_serves_the_sticky_note_as_note_and_the_other_blocks_as_they_are() -> None:
    from app.domain.lessons.screens import RenderContext, render_screen

    screen = {
        "id": "s",
        "type": "content",
        "title": "T",
        "body": ["One."],
        "steps": [{"n": "1", "title": "A", "text": "B"}],
        "dodont": {"do": ["x"], "dont": ["y"]},
        "example": {"line1": "Mom,", "line2": "I am here."},
    }
    out = render_screen(screen, RenderContext(None, {}, False))
    assert out["note"] == {"line1": "Mom,", "line2": "I am here."}
    assert "example" not in out
    assert out["steps"] == screen["steps"] and out["dodont"] == screen["dodont"]
