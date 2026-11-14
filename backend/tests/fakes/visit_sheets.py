from uuid import UUID

from app.domain.visit_sheet.entities import VisitSheet


class InMemoryVisitSheetRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, VisitSheet] = {}

    async def get(self, session_id: UUID) -> VisitSheet | None:
        return self.rows.get(session_id)

    async def save(self, sheet: VisitSheet) -> None:
        self.rows[sheet.session_id] = sheet
