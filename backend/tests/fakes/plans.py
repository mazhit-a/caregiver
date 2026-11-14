from typing import Literal
from uuid import UUID

from app.domain.lessons.plans import ConfidenceRatings
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
        self.ratings: dict[UUID, ConfidenceRatings] = {}

    async def get_day0(self, session_id: UUID) -> int | None:
        return self.day0.get(session_id)

    async def save_day0(self, session_id: UUID, value: int) -> None:
        self.day0[session_id] = value

    async def get_ratings(self, session_id: UUID) -> ConfidenceRatings:
        return self.ratings.get(session_id, ConfidenceRatings())

    async def save_ratings(
        self, session_id: UUID, slot: Literal["first", "latest"], ratings: dict[str, int]
    ) -> None:
        current = self.ratings.get(session_id, ConfidenceRatings())
        self.ratings[session_id] = (
            ConfidenceRatings(ratings, current.latest)
            if slot == "first"
            else ConfidenceRatings(current.first, ratings)
        )
