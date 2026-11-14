"""Postgres EventLog: the catalog cleans every event before it is written."""

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events.catalog import clean_event
from app.infrastructure.db.orm_models import EventRow


class SqlEventLog:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self, session_id: UUID, name: str, props: Mapping[str, object], app_at: datetime
    ) -> None:
        event = clean_event(name, props)
        self._db.add(
            EventRow(session_id=session_id, name=event.name, props=event.props, app_at=app_at)
        )
