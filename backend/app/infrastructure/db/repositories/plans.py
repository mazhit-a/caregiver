"""Postgres repository for the plan snapshot of a session."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.plan.entities import StoredPlan
from app.infrastructure.db.orm_models import PlanRow
from app.infrastructure.db.plan_snapshot import plan_from_snapshot, plan_to_snapshot


class SqlPlanRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID) -> StoredPlan | None:
        result = await self._db.execute(select(PlanRow).where(PlanRow.session_id == session_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return StoredPlan(
            session_id=row.session_id,
            plan=plan_from_snapshot(row.snapshot),
            rules_version=row.rules_version,
            content_version=row.content_version,
            lessons_per_week=row.lessons_per_week,
            gift_phrase_ids=tuple(row.gift_phrase_ids),
            built_at=row.built_at,
        )

    async def save(self, plan: StoredPlan) -> None:
        values = {
            "snapshot": plan_to_snapshot(plan.plan),
            "rules_version": plan.rules_version,
            "content_version": plan.content_version,
            "lessons_per_week": plan.lessons_per_week,
            "gift_phrase_ids": list(plan.gift_phrase_ids),
            "built_at": plan.built_at,
        }
        stmt = insert(PlanRow).values(session_id=plan.session_id, **values)
        await self._db.execute(
            stmt.on_conflict_do_update(index_elements=[PlanRow.session_id], set_=values)
        )
