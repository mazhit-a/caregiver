"""Postgres repositories for check-in answers and observations."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.today.checkins import Checkin, Observation, ObservationSource, Outcome
from app.infrastructure.db.orm_models import CheckinRow, ObservationRow


class SqlCheckinRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID, lesson_id: str) -> Checkin | None:
        row = await self._db.get(CheckinRow, (session_id, lesson_id))
        return None if row is None else _checkin(row)

    async def add(self, checkin: Checkin) -> None:
        self._db.add(
            CheckinRow(
                session_id=checkin.session_id,
                lesson_id=checkin.lesson_id,
                came_up=checkin.came_up,
                outcome=checkin.outcome,
                answered_at=checkin.answered_at,
            )
        )

    async def list_for_session(self, session_id: UUID) -> list[Checkin]:
        result = await self._db.execute(
            select(CheckinRow)
            .where(CheckinRow.session_id == session_id)
            .order_by(CheckinRow.answered_at, CheckinRow.lesson_id)
        )
        return [_checkin(row) for row in result.scalars()]


def _checkin(row: CheckinRow) -> Checkin:
    return Checkin(
        row.session_id,
        row.lesson_id,
        row.came_up,
        cast(Outcome | None, row.outcome),
        row.answered_at,
    )


class SqlObservationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, observation: Observation) -> None:
        self._db.add(
            ObservationRow(
                id=observation.id,
                session_id=observation.session_id,
                lesson_id=observation.lesson_id,
                source=observation.source,
                text=observation.text,
                add_to_visit_sheet=observation.add_to_visit_sheet,
                created_at=observation.created_at,
            )
        )

    async def list_for_session(self, session_id: UUID) -> list[Observation]:
        result = await self._db.execute(
            select(ObservationRow)
            .where(ObservationRow.session_id == session_id)
            .order_by(ObservationRow.created_at, ObservationRow.id)
        )
        return [
            Observation(
                row.id,
                row.session_id,
                row.lesson_id,
                cast(ObservationSource, row.source),
                row.text,
                row.add_to_visit_sheet,
                row.created_at,
            )
            for row in result.scalars()
        ]
