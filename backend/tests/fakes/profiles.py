from dataclasses import replace
from uuid import UUID

from app.domain.profile.entities import Profile


class InMemoryProfileRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, Profile] = {}

    async def get(self, session_id: UUID) -> Profile | None:
        return self.rows.get(session_id)

    async def save(self, profile: Profile) -> None:
        self.rows[profile.session_id] = replace(profile)
