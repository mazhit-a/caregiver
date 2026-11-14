import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.domain.lessons.errors import LessonContentError
from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS, RenderedLesson, render_lesson
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
    assert "doctor" in screen(in_person, "s2_scenario")["setup"]
    assert "calls" in screen(phone, "s2_scenario")["setup"]
    assert screen(in_person, "s2_scenario")["answers"] != screen(phone, "s2_scenario")["answers"]


def test_both_uses_in_person_texts_plus_the_phone_tip(content: JsonContentProvider) -> None:
    both = lesson(content, "both")
    in_person = lesson(content, "in_person")
    assert screen(both, "s2_scenario")["answers"] == screen(in_person, "s2_scenario")["answers"]
    assert screen(both, "s5_aha")["extra"].startswith("On the phone")
    assert "extra" not in screen(in_person, "s5_aha")


def test_without_a_variant_only_screens_up_to_the_setup_question_show(
    content: JsonContentProvider,
) -> None:
    result = lesson(content, None)
    assert [s["id"] for s in result.screens] == ["s1_setup"]
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
    assert "confidenceCheck" in screen(lesson(content, "phone", first=True), "s9_wrap")
    assert "confidenceCheck" not in screen(lesson(content, "phone", first=False), "s9_wrap")
