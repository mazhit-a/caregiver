"""Visit sheet request and response schemas. Limits come from the domain, one source."""

from datetime import date, datetime

from pydantic import Field, model_validator

from app.domain.visit_sheet.entities import (
    MAX_CUSTOM_QUESTION_LENGTH,
    MAX_DOCTOR_LENGTH,
    MAX_FAMILY_NOTES_LENGTH,
    MAX_QUESTIONS,
)
from app.presentation.api.schemas.base import CamelModel


class QuestionIn(CamelModel):
    """A question from the list (`id`) or one of the family's own (`text`)."""

    id: str | None = Field(default=None, min_length=1, max_length=64)
    text: str | None = Field(default=None, min_length=1, max_length=MAX_CUSTOM_QUESTION_LENGTH)

    @model_validator(mode="after")
    def _one_of(self) -> "QuestionIn":
        if (self.id is None) == (self.text is None):
            raise ValueError("send either id or text")
        return self


class VisitSheetRequest(CamelModel):
    doctor: str | None = Field(default=None, max_length=MAX_DOCTOR_LENGTH)
    visit_date: date | None = None
    family_notes: str = Field(default="", max_length=MAX_FAMILY_NOTES_LENGTH)
    questions: list[QuestionIn] = Field(default_factory=list, max_length=MAX_QUESTIONS)


class QuestionOut(CamelModel):
    id: str | None
    text: str
    custom: bool


class BankQuestionOut(CamelModel):
    id: str
    text: str


class SuggestedNoteOut(CamelModel):
    id: str
    text: str
    created_at: datetime


class VisitSheetResponse(CamelModel):
    doctor: str | None
    visit_date: date | None
    family_notes: str
    questions: list[QuestionOut]
    bank: list[BankQuestionOut]
    suggested_notes: list[SuggestedNoteOut]
    footer: str
    updated_at: datetime | None
