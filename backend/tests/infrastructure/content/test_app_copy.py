from pathlib import Path

import pytest

from app.domain.app_copy.render import render_app_copy
from app.domain.shared.labels import with_display_name
from app.infrastructure.content.provider import JsonContentProvider

REAL_CONTENT = Path(__file__).resolve().parents[4] / "content"
KEYS = JsonContentProvider.from_directory(REAL_CONTENT).recipient_keys()


def _all_texts(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    assert isinstance(node, dict)
    return [text for child in node.values() for text in _all_texts(child)]


def test_the_app_copy_file_is_loaded_with_every_section() -> None:
    copy = JsonContentProvider.from_directory(REAL_CONTENT).app_copy()
    assert set(copy) == {
        "nav",
        "plan",
        "profile",
        "care_card",
        "visit_sheet",
        "skills",
        "settings",
        "welcome",
        "lesson",
    }


def test_the_lesson_block_has_the_player_labels() -> None:
    lesson = JsonContentProvider.from_directory(REAL_CONTENT).app_copy()["lesson"]
    assert lesson["verdict_labels"] == {
        "best": "Good instinct",
        "okay": "Noted",
        "try_again": "Very common",
    }
    assert set(lesson["quiz"]) == {"right", "wrong"}
    assert set(lesson["builder"]) == {"all_correct", "not_yet"}
    assert set(lesson["do_skip"]) == {"do_label", "skip_label"}


@pytest.mark.parametrize("key", KEYS)
def test_every_recipient_key_renders_without_placeholders_or_markdown(key: str) -> None:
    content = JsonContentProvider.from_directory(REAL_CONTENT)
    rendered = render_app_copy(content.app_copy(), content.recipient_labels(key))
    texts = _all_texts(rendered)
    assert texts
    for text in texts:
        assert text and "{" not in text and "}" not in text and "**" not in text


@pytest.mark.parametrize("key", KEYS)
def test_display_name_replaces_the_label_for_every_key(key: str) -> None:
    content = JsonContentProvider.from_directory(REAL_CONTENT)
    labels = with_display_name(content.recipient_labels(key), "Margaret")
    rendered = render_app_copy(content.app_copy(), labels)
    assert rendered["nav"]["profile_page"] == "Margaret's page"
    assert rendered["profile"]["works_title"] == "What works with Margaret"


def test_gentle_exit_entry_is_neutral_for_every_recipient() -> None:
    content = JsonContentProvider.from_directory(REAL_CONTENT)
    for key in ("both", "mom"):
        rendered = render_app_copy(content.app_copy(), content.recipient_labels(key))
        assert rendered["settings"]["gentle_exit_entry"] == "Close my plan and delete my data"
