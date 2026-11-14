"""The visit sheet entity, its limits and its validation. Text is kept exactly as typed."""

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from app.domain.shared.errors import DomainError

MAX_DOCTOR_LENGTH = 120
MAX_FAMILY_NOTES_LENGTH = 2000
MAX_QUESTIONS = 20
MAX_CUSTOM_QUESTIONS = 10
MAX_CUSTOM_QUESTION_LENGTH = 300


class InvalidVisitSheet(DomainError):
    code = "invalid_visit_sheet"


class UnknownVisitQuestion(DomainError):
    code = "unknown_visit_question"

    def __init__(self, question_ids: list[str]) -> None:
        super().__init__(
            "Some questions are not in the question list.", {"questionIds": question_ids}
        )


@dataclass(frozen=True)
class VisitQuestionItem:
    """One entry of the sheet's ordered list: a bank question (`bank_id`) or the family's own
    (`custom_text`). Exactly one is set."""

    bank_id: str | None = None
    custom_text: str | None = None


@dataclass(frozen=True)
class VisitSheet:
    session_id: UUID
    doctor: str | None = None
    visit_date: date | None = None
    family_notes: str = ""
    questions: tuple[VisitQuestionItem, ...] = field(default=())
    updated_at: datetime | None = None


def validate_visit_sheet(sheet: VisitSheet, bank_ids: frozenset[str]) -> None:
    """Size limits first, then bank ids; both are 422 and never echo the caregiver's words."""
    if sheet.doctor is not None and len(sheet.doctor) > MAX_DOCTOR_LENGTH:
        raise InvalidVisitSheet(
            f"The doctor's name can be at most {MAX_DOCTOR_LENGTH} characters.",
            {"field": "doctor", "max": MAX_DOCTOR_LENGTH},
        )
    if len(sheet.family_notes) > MAX_FAMILY_NOTES_LENGTH:
        raise InvalidVisitSheet(
            f"Family notes can be at most {MAX_FAMILY_NOTES_LENGTH} characters.",
            {"field": "familyNotes", "max": MAX_FAMILY_NOTES_LENGTH},
        )
    if len(sheet.questions) > MAX_QUESTIONS:
        raise InvalidVisitSheet(
            f"The sheet can hold at most {MAX_QUESTIONS} questions.",
            {"field": "questions", "max": MAX_QUESTIONS},
        )
    custom = [q.custom_text for q in sheet.questions if q.custom_text is not None]
    if len(custom) > MAX_CUSTOM_QUESTIONS:
        raise InvalidVisitSheet(
            f"You can add at most {MAX_CUSTOM_QUESTIONS} questions of your own.",
            {"field": "questions", "maxCustom": MAX_CUSTOM_QUESTIONS},
        )
    for item in sheet.questions:
        if (item.bank_id is None) == (item.custom_text is None):
            raise InvalidVisitSheet("Each question is either from the list or your own.")
    for text in custom:
        if not text.strip() or len(text) > MAX_CUSTOM_QUESTION_LENGTH:
            raise InvalidVisitSheet(
                f"Your own questions need 1 to {MAX_CUSTOM_QUESTION_LENGTH} characters.",
                {"field": "questions", "maxLength": MAX_CUSTOM_QUESTION_LENGTH},
            )
    unknown = [q.bank_id for q in sheet.questions if q.bank_id and q.bank_id not in bank_ids]
    if unknown:
        raise UnknownVisitQuestion(unknown)
    chosen = [q.bank_id for q in sheet.questions if q.bank_id]
    if len(set(chosen)) != len(chosen):
        raise InvalidVisitSheet("A question from the list can be added once.")


@dataclass(frozen=True)
class BankQuestion:
    id: str
    text: str


@dataclass(frozen=True)
class VisitQuestionBank:
    """The question bank and footer of `visit-questions.json`."""

    footer: str
    questions: tuple[BankQuestion, ...]
