from dataclasses import replace
from uuid import UUID

from app.domain.lessons.plans import IfThenPlan, Task


class InMemoryIfThenPlanRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, str], IfThenPlan] = {}

    async def get(self, session_id: UUID, lesson_id: str) -> IfThenPlan | None:
        return self.rows.get((session_id, lesson_id))

    async def save(self, plan: IfThenPlan) -> None:
        self.rows[(plan.session_id, plan.lesson_id)] = plan


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, str], Task] = {}

    async def get(self, session_id: UUID, lesson_id: str) -> Task | None:
        return self.rows.get((session_id, lesson_id))

    async def save(self, task: Task) -> None:
        existing = self.rows.get((task.session_id, task.lesson_id))
        self.rows[(task.session_id, task.lesson_id)] = replace(
            task, done_at=existing.done_at if existing else task.done_at
        )
