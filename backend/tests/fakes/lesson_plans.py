from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.domain.lessons.plans import IfThenPlan, Task


class InMemoryIfThenPlanRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, str], IfThenPlan] = {}

    async def get(self, session_id: UUID, lesson_id: str) -> IfThenPlan | None:
        return self.rows.get((session_id, lesson_id))

    async def latest(self, session_id: UUID) -> IfThenPlan | None:
        mine = [p for p in self.rows.values() if p.session_id == session_id]
        return max(mine, key=lambda p: (p.created_at, p.lesson_id), default=None)

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

    async def mark_done(self, session_id: UUID, lesson_id: str, done_at: datetime) -> None:
        task = self.rows.get((session_id, lesson_id))
        if task is not None:
            self.rows[(session_id, lesson_id)] = replace(task, done_at=done_at)

    async def list_for_session(self, session_id: UUID) -> list[Task]:
        return sorted(
            (t for t in self.rows.values() if t.session_id == session_id),
            key=lambda t: t.created_at,
        )
