"""Postgres repository for the visit sheet (one row per session)."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.visit_sheet.entities import VisitQuestionItem, VisitSheet
from app.infrastructure.db.orm_models import VisitSheetRow


class SqlVisitSheetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID) -> VisitSheet | None:
        row = await self._db.get(VisitSheetRow, session_id)
        if row is None:
            return None
        return VisitSheet(
            session_id=row.session_id,
            doctor=row.doctor,
            visit_date=row.visit_date,
            family_notes=row.family_notes,
            questions=tuple(VisitQuestionItem(q.get("id"), q.get("text")) for q in row.questions),
            updated_at=row.updated_at,
        )

    async def save(self, sheet: VisitSheet) -> None:
        if sheet.updated_at is None:
            raise ValueError("A saved visit sheet needs its update time.")
        values = {
            "session_id": sheet.session_id,
            "doctor": sheet.doctor,
            "visit_date": sheet.visit_date,
            "family_notes": sheet.family_notes,
            "questions": [
                {"id": q.bank_id} if q.bank_id is not None else {"text": q.custom_text}
                for q in sheet.questions
            ],
            "updated_at": sheet.updated_at,
        }
        stmt = insert(VisitSheetRow).values(**values)
        update = {k: v for k, v in values.items() if k != "session_id"}
        await self._db.execute(
            stmt.on_conflict_do_update(index_elements=["session_id"], set_=update)
        )
