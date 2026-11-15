import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.domain.lessons.errors import LessonContentError
from app.domain.lessons.screens import (
    RUNTIME_PLACEHOLDERS,
    RenderedLesson,
    has_phrases_review,
    render_lesson,
    with_saved_phrases,
)
from app.domain.lessons.variants import pick
from app.infrastructure.content.provider import JsonContentProvider

REPO = Path(__file__).resolve().parents[4]
BLANKS = dict.fromkeys(RUNTIME_PLACEHOLDERS, "")


@pytest.fixture(scope="module")
def content() -> JsonContentProvider:
    return JsonContentProvider.from_directory(REPO / "content")


def lesson(
    content: JsonContentProvider,
    variant: str | None,
    recipient: str = "mom",
    first: bool = True,
) -> RenderedLesson:
    data = content.render_lesson("m1_l1", recipient, variant, BLANKS)
    return render_lesson(data, variant, first)


def screen(result: RenderedLesson, screen_id: str) -> dict[str, Any]:
    return next(s for s in result.screens if s["id"] == screen_id)


def test_pick_goes_through_the_variant_map_and_falls_back_to_the_key() -> None:
    options = {"in_person": 1, "phone": 2}
    assert pick(options, "both", {"both": "in_person"}) == 1
    assert pick(options, "phone", {"both": "in_person"}) == 2
    assert pick({"default": 3}, None) == 3


def test_pick_with_an_uncovered_variant_is_a_content_error() -> None:
    with pytest.raises(LessonContentError):
        pick({"in_person": 1}, "phone", {})


def test_variant_changes_examples_but_not_the_screen_path(content: JsonContentProvider) -> None:
    in_person = lesson(content, "in_person")
    phone = lesson(content, "phone")
    assert [s["id"] for s in in_person.screens] == [s["id"] for s in phone.screens]
    assert "appointment" in screen(in_person, "scenario")["setup"]
    assert "calls" in screen(phone, "scenario")["setup"]
    assert screen(in_person, "scenario")["answers"] != screen(phone, "scenario")["answers"]


def test_both_and_not_yet_use_the_in_person_scenario(content: JsonContentProvider) -> None:
    in_person = lesson(content, "in_person")
    for variant in ("both", "not_yet"):
        other = lesson(content, variant)
        assert screen(other, "scenario")["answers"] == screen(in_person, "scenario")["answers"]
    both_tools = screen(lesson(content, "both"), "tools")["body"]
    assert both_tools == screen(in_person, "tools")["body"]
    assert screen(lesson(content, "phone"), "tools")["body"] != both_tools


def test_without_a_variant_only_screens_up_to_the_setup_screen_show(
    content: JsonContentProvider,
) -> None:
    result = lesson(content, None)
    assert [s["id"] for s in result.screens] == ["intro", "setup"]
    assert result.variant is None


def test_screens_never_carry_server_only_fields(content: JsonContentProvider) -> None:
    text = json.dumps(lesson(content, "in_person").screens)
    for forbidden in ('"verdict"', '"feedback"', '"savePhrase"', '"response"', '"correct"'):
        assert forbidden not in text
    for key in ("storeAs", "allCorrect", "responseDefault", "promptFile", "fallbackScenarios"):
        assert key not in text
    assert "Kind and practical" not in text  # a feedback text of the scenario


def test_runtime_placeholders_never_reach_the_output(content: JsonContentProvider) -> None:
    text = json.dumps(lesson(content, "phone").screens)
    assert not re.search(r"\{\w+\}", text) and "firstVsLast" not in text


def test_confidence_check_only_in_the_first_lesson(content: JsonContentProvider) -> None:
    assert "confidenceCheck" in screen(lesson(content, "phone", first=True), "wrap")
    assert "confidenceCheck" not in screen(lesson(content, "phone", first=False), "wrap")


def review_lesson(content: JsonContentProvider) -> RenderedLesson:
    data = content.render_lesson("m1_l5", "mom", None, BLANKS)
    return render_lesson(data, None, False)


def test_phrases_review_screen_renders_empty_until_filled(content: JsonContentProvider) -> None:
    result = review_lesson(content)
    assert has_phrases_review(result) and not has_phrases_review(lesson(content, "in_person"))
    shown = screen(result, "s2_phrases")
    assert shown["phrases"] == [] and shown["emptyText"]


def test_with_saved_phrases_fills_only_the_review_screen(content: JsonContentProvider) -> None:
    result = review_lesson(content)
    saved = [{"id": "1", "text": "I'm here.", "source": "roleplay", "lessonId": "m1_l1"}]
    filled = with_saved_phrases(result, saved)
    assert screen(filled, "s2_phrases")["phrases"] == saved
    assert [s for s in filled.screens if s["id"] != "s2_phrases"] == [
        s for s in result.screens if s["id"] != "s2_phrases"
    ]
    assert screen(result, "s2_phrases")["phrases"] == []  # the input is not changed
