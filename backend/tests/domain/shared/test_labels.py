import pytest

from app.domain.shared.labels import (
    RecipientLabels,
    UnknownPlaceholder,
    lesson_labels,
    render_text,
)

MOM = RecipientLabels("Mom", "Mom's", "she", "her", "was", "is", "has", "lives")
BOTH = RecipientLabels(
    "your parents", "your parents'", "they", "them", "were", "are", "have", "live"
)


def test_render_fills_all_eleven_placeholders() -> None:
    text = "{recipient} {Recipient} {possessive} {Possessive} {pronoun} {Pronoun} {object}"
    text += " {was} {is} {has} {lives}"
    assert render_text(text, MOM) == "Mom Mom Mom's Mom's she She her was is has lives"


def test_capitalised_placeholder_capitalises_first_letter_only() -> None:
    assert render_text("{Recipient} {Pronoun}", BOTH) == "Your parents They"


def test_missing_placeholder_value_raises() -> None:
    with pytest.raises(UnknownPlaceholder) as info:
        render_text("Your phrase: {savedPhrase}", MOM)
    assert info.value.name == "savedPhrase"


def test_extra_values_fill_runtime_placeholders() -> None:
    assert render_text("Said: {savedPhrase}", MOM, {"savedPhrase": "hello"}) == "Said: hello"


def test_text_without_placeholders_is_unchanged() -> None:
    assert render_text("Nothing here.", MOM) == "Nothing here."


def test_labels_for_both_use_singular_parent() -> None:
    labels = lesson_labels("both", {"both": BOTH, "mom": MOM})
    assert render_text("{Recipient} {is} calm; ask {object} about {possessive} day.", labels) == (
        "Your parent is calm; ask them about your parent's day."
    )


def test_lesson_labels_for_other_keys_are_the_quiz_labels() -> None:
    assert lesson_labels("mom", {"both": BOTH, "mom": MOM}) is MOM
