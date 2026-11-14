from uuid import UUID

from app.domain.plan.entities import StoredPlan


class InMemoryPlanRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, StoredPlan] = {}

    async def get(self, session_id: UUID) -> StoredPlan | None:
        return self.rows.get(session_id)

    async def save(self, plan: StoredPlan) -> None:
        self.rows[plan.session_id] = plan


class InMemoryConfidenceRepository:
    def __init__(self) -> None:
        self.day0: dict[UUID, int] = {}

    async def get_day0(self, session_id: UUID) -> int | None:
        return self.day0.get(session_id)

    async def save_day0(self, session_id: UUID, value: int) -> None:
        self.day0[session_id] = value
