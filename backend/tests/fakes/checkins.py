from uuid import UUID

from app.domain.today.checkins import Checkin, Observation


class InMemoryCheckinRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, str], Checkin] = {}

    async def get(self, session_id: UUID, lesson_id: str) -> Checkin | None:
        return self.rows.get((session_id, lesson_id))

    async def add(self, checkin: Checkin) -> None:
        self.rows[(checkin.session_id, checkin.lesson_id)] = checkin

    async def list_for_session(self, session_id: UUID) -> list[Checkin]:
        found = [c for c in self.rows.values() if c.session_id == session_id]
        return sorted(found, key=lambda c: (c.answered_at, c.lesson_id))


class InMemoryObservationRepository:
    def __init__(self) -> None:
        self.rows: list[Observation] = []

    async def add(self, observation: Observation) -> None:
        self.rows.append(observation)

    async def list_for_session(self, session_id: UUID) -> list[Observation]:
        return sorted(
            (o for o in self.rows if o.session_id == session_id), key=lambda o: o.created_at
        )
