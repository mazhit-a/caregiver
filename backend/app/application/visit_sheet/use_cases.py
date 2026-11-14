"""`GET/PUT /api/visit-sheet`. The sheet belongs to one session and is never published."""

from dataclasses import dataclass
from datetime import date, datetime

from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.session.entities import Session
from app.domain.visit_sheet.entities import (
    VisitQuestionItem,
    VisitSheet,
    validate_visit_sheet,
)


@dataclass(frozen=True)
class QuestionView:
    id: str | None
    text: str
    custom: bool


@dataclass(frozen=True)
class BankQuestionView:
    id: str
    text: str


@dataclass(frozen=True)
class SuggestedNote:
    id: str
    text: str
    created_at: datetime


@dataclass(frozen=True)
class VisitSheetView:
    doctor: str | None
    visit_date: date | None
    family_notes: str
    questions: list[QuestionView]
    bank: list[BankQuestionView]
    suggested_notes: list[SuggestedNote]
    footer: str
    updated_at: datetime | None


def _is_known(item: VisitQuestionItem, texts: dict[str, str]) -> bool:
    """A bank question that content no longer has is left out rather than failing the read."""
    return item.bank_id is None or item.bank_id in texts


def _question_view(item: VisitQuestionItem, texts: dict[str, str]) -> QuestionView:
    if item.bank_id is not None:
        return QuestionView(item.bank_id, texts[item.bank_id], False)
    return QuestionView(None, item.custom_text or "", True)


async def _view(uow: UnitOfWork, content: ContentProvider, session: Session) -> VisitSheetView:
    sheet = await uow.visit_sheets.get(session.id) or VisitSheet(session.id)
    questions = content.visit_questions()
    texts = {q.id: q.text for q in questions.questions}
    observations = await uow.observations.list_for_session(session.id)
    return VisitSheetView(
        doctor=sheet.doctor,
        visit_date=sheet.visit_date,
        family_notes=sheet.family_notes,
        questions=[_question_view(q, texts) for q in sheet.questions if _is_known(q, texts)],
        bank=[BankQuestionView(q.id, q.text) for q in questions.questions],
        suggested_notes=[
            SuggestedNote(str(o.id), o.text, o.created_at)
            for o in observations
            if o.add_to_visit_sheet
        ],
        footer=questions.footer,
        updated_at=sheet.updated_at,
    )


class GetVisitSheet:
    def __init__(self, uow: UnitOfWork, content: ContentProvider) -> None:
        self._uow = uow
        self._content = content

    async def execute(self, session: Session) -> VisitSheetView:
        async with self._uow:
            return await _view(self._uow, self._content, session)


@dataclass(frozen=True)
class VisitSheetInput:
    doctor: str | None
    visit_date: date | None
    family_notes: str
    questions: tuple[VisitQuestionItem, ...]


class UpdateVisitSheet:
    """Replaces the whole sheet; the caregiver's words are stored exactly as typed."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock

    async def execute(self, session: Session, data: VisitSheetInput) -> VisitSheetView:
        sheet = VisitSheet(
            session.id,
            data.doctor,
            data.visit_date,
            data.family_notes,
            data.questions,
            session.app_now(self._clock.now()),
        )
        bank_ids = frozenset(q.id for q in self._content.visit_questions().questions)
        validate_visit_sheet(sheet, bank_ids)
        async with self._uow:
            await self._uow.visit_sheets.save(sheet)
            await self._uow.commit()
            return await _view(self._uow, self._content, session)
