from uuid import UUID

from app.domain.lessons.progress import ScenarioAnswer


class InMemoryScenarioAnswerRepository:
    def __init__(self) -> None:
        self.rows: list[ScenarioAnswer] = []

    async def add(self, answer: ScenarioAnswer) -> None:
        self.rows.append(answer)

    async def list_for_lesson(self, session_id: UUID, lesson_id: str) -> list[ScenarioAnswer]:
        return [r for r in self.rows if r.session_id == session_id and r.lesson_id == lesson_id]
