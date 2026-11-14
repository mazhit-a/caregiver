import json
import shutil
from pathlib import Path

import pytest

from app.domain.shared.labels import UnknownPlaceholder
from app.infrastructure.content.loader import ContentLoadError, load_content
from app.infrastructure.content.provider import JsonContentProvider, UnknownContentReference

REAL_CONTENT = Path(__file__).resolve().parents[4] / "content"
RUNTIME_VALUES = {"savedPhrase": "a saved phrase", "firstScore": "1", "lastScore": "3"}


@pytest.fixture
def content_copy(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(REAL_CONTENT, target)
    return target


def _strings(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [t for item in node for t in _strings(item)]
    if isinstance(node, dict):
        return [t for value in node.values() for t in _strings(value)]
    return []


def _edit(path: Path, change: object) -> None:
    data = json.loads(path.read_text())
    assert callable(change)
    change(data)
    path.write_text(json.dumps(data))


def test_all_content_files_load() -> None:
    bundle = load_content(REAL_CONTENT)
    assert bundle.quiz.version == 3
    assert {q.id for q in bundle.quiz.questions} >= {"q1_recipient", "q11_confidence"}
    assert len(bundle.plan_rules.modules) >= 6
    assert bundle.phrases.phrases
    assert [p.id for p in bundle.pricing.plans] == ["four_week", "twelve_week"]
    assert bundle.funnel_copy.common["notMedicalAdvice"]
    assert set(bundle.lessons) == {"m1_l1", "m1_l2", "m1_l3", "m1_l4", "m1_l5"}
    assert len(bundle.content_version) == 16


def test_every_lesson_renders_for_every_recipient_key_and_variant() -> None:
    provider = JsonContentProvider.from_directory(REAL_CONTENT)
    keys = provider.recipient_keys()
    assert set(keys) == {"mom", "dad", "both", "in_law", "other"}
    variants = provider.lesson_variants("m1_l1")
    assert variants == ["in_person", "phone", "both", "not_yet"]
    for lesson_id in provider.lesson_ids():
        for key in keys:
            for variant in provider.lesson_variants(lesson_id):
                rendered = provider.render_lesson(lesson_id, key, variant, RUNTIME_VALUES)
                assert not [t for t in _strings(rendered) if "{" in t or "}" in t], (
                    lesson_id,
                    key,
                    variant,
                )
                assert "notes" not in rendered


def test_rendered_lesson_uses_recipient_label_and_singular_parent_for_both() -> None:
    provider = JsonContentProvider.from_directory(REAL_CONTENT)
    mom = provider.render_lesson("m1_l1", "mom", "in_person", RUNTIME_VALUES)
    both = provider.render_lesson("m1_l1", "both", "in_person", RUNTIME_VALUES)
    assert mom["title"] == "When Mom asks again"
    assert both["title"] == "When your parent asks again"


def test_render_without_runtime_values_raises() -> None:
    provider = JsonContentProvider.from_directory(REAL_CONTENT)
    with pytest.raises(UnknownPlaceholder):
        provider.render_lesson("m1_l1", "mom", "in_person")


def test_unknown_lesson_recipient_or_variant_raises() -> None:
    provider = JsonContentProvider.from_directory(REAL_CONTENT)
    with pytest.raises(UnknownContentReference):
        provider.render_lesson("nope", "mom")
    with pytest.raises(UnknownContentReference):
        provider.render_lesson("m1_l1", "cat", None, RUNTIME_VALUES)
    with pytest.raises(UnknownContentReference):
        provider.render_lesson("m1_l1", "mom", "nope", RUNTIME_VALUES)


def test_invalid_lesson_screen_type_names_file_and_field(content_copy: Path) -> None:
    def break_screen(data: dict[str, list[dict[str, str]]]) -> None:
        data["screens"][2]["type"] = "quiz_show"

    _edit(content_copy / "lessons" / "m1_l1.json", break_screen)
    with pytest.raises(ContentLoadError) as info:
        load_content(content_copy)
    message = str(info.value)
    assert "lessons/m1_l1.json" in message
    assert "screens.2" in message


def test_missing_required_field_names_file_and_field(content_copy: Path) -> None:
    def drop_title(data: dict[str, object]) -> None:
        del data["title"]

    _edit(content_copy / "lessons" / "m1_l1.json", drop_title)
    with pytest.raises(ContentLoadError, match=r"lessons/m1_l1\.json: title"):
        load_content(content_copy)


def test_invalid_json_and_missing_file_are_reported(content_copy: Path) -> None:
    (content_copy / "phrases.json").write_text("{not json")
    with pytest.raises(ContentLoadError, match=r"phrases\.json: invalid JSON"):
        load_content(content_copy)
    (content_copy / "phrases.json").unlink()
    with pytest.raises(ContentLoadError, match=r"phrases\.json: cannot read"):
        load_content(content_copy)


def test_lesson_without_variants_is_valid(content_copy: Path) -> None:
    def strip_setup(data: dict[str, list[dict[str, str]]]) -> None:
        data["screens"] = [s for s in data["screens"] if s["type"] != "setup_question"]

    _edit(content_copy / "lessons" / "m1_l1.json", strip_setup)
    bundle = load_content(content_copy)
    assert bundle.lessons["m1_l1"].variant_ids() == []


def test_content_version_changes_when_a_file_changes(content_copy: Path) -> None:
    before = load_content(content_copy).content_version
    assert load_content(content_copy).content_version == before

    def bump(data: dict[str, object]) -> None:
        data["currency"] = "EUR"

    _edit(content_copy / "pricing.json", bump)
    assert load_content(content_copy).content_version != before


def test_content_version_changes_when_a_lesson_file_changes(content_copy: Path) -> None:
    before = load_content(content_copy).content_version

    def retitle(data: dict[str, object]) -> None:
        data["title"] = "Another {recipient} title"

    _edit(content_copy / "lessons" / "m1_l1.json", retitle)
    assert load_content(content_copy).content_version != before


def test_funnel_copy_v2_privacy_wording_and_new_keys() -> None:
    copy = load_content(REAL_CONTENT).funnel_copy
    saved = "Saved privately to this session. No account, no name needed."
    assert copy.version == 2
    assert copy.common["privacyShort"] == saved
    assert copy.landing.trust[2] == saved
    assert copy.landing.faq[3].a.startswith(saved)
    assert copy.quiz_intro.title == "Let's build your plan"
    assert saved in copy.quiz_intro.body
    assert copy.quiz.health_note.startswith("This page has no ad tracking.")
    assert copy.plan_preview.plan.highlight_label == "For now"


def test_funnel_copy_no_longer_claims_answers_stay_in_the_browser() -> None:
    raw = json.loads((REAL_CONTENT / "funnel-copy.json").read_text())
    raw.pop("notes", None)
    for text in _strings(raw):
        assert "in this browser" not in text
        assert "your browser" not in text
