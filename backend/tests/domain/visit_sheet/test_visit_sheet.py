from uuid import uuid4

import pytest

from app.domain.visit_sheet.entities import (
    MAX_CUSTOM_QUESTION_LENGTH,
    MAX_CUSTOM_QUESTIONS,
    MAX_FAMILY_NOTES_LENGTH,
    MAX_QUESTIONS,
    InvalidVisitSheet,
    UnknownVisitQuestion,
    VisitQuestionItem,
    VisitSheet,
    validate_visit_sheet,
)

BANK = frozenset({"q_a", "q_b"})


def sheet(*items: VisitQuestionItem, notes: str = "", doctor: str | None = None) -> VisitSheet:
    return VisitSheet(uuid4(), doctor, None, notes, tuple(items))


def test_valid_sheet_passes() -> None:
    validate_visit_sheet(
        sheet(VisitQuestionItem("q_b"), VisitQuestionItem(None, "Mine?"), notes="x"), BANK
    )


def test_unknown_bank_id_lists_the_ids() -> None:
    with pytest.raises(UnknownVisitQuestion) as err:
        validate_visit_sheet(sheet(VisitQuestionItem("q_a"), VisitQuestionItem("nope")), BANK)
    assert err.value.details == {"questionIds": ["nope"]}


def test_custom_cap_and_length() -> None:
    many = [VisitQuestionItem(None, "q")] * (MAX_CUSTOM_QUESTIONS + 1)
    with pytest.raises(InvalidVisitSheet):
        validate_visit_sheet(sheet(*many), BANK)
    with pytest.raises(InvalidVisitSheet):
        validate_visit_sheet(
            sheet(VisitQuestionItem(None, "x" * (MAX_CUSTOM_QUESTION_LENGTH + 1))), BANK
        )
    with pytest.raises(InvalidVisitSheet):
        validate_visit_sheet(sheet(VisitQuestionItem(None, "   ")), BANK)


def test_total_notes_and_duplicate_limits() -> None:
    with pytest.raises(InvalidVisitSheet):
        validate_visit_sheet(sheet(*[VisitQuestionItem("q_a")] * 2), BANK)
    with pytest.raises(InvalidVisitSheet):
        validate_visit_sheet(sheet(notes="x" * (MAX_FAMILY_NOTES_LENGTH + 1)), BANK)
    with pytest.raises(InvalidVisitSheet):
        validate_visit_sheet(sheet(*[VisitQuestionItem(None, "q")] * (MAX_QUESTIONS + 1)), BANK)
    with pytest.raises(InvalidVisitSheet):
        validate_visit_sheet(sheet(VisitQuestionItem("q_a", "also text")), BANK)
