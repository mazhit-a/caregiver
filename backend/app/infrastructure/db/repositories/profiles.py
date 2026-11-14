"""Postgres repository for the profile (one row per session)."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.profile.entities import Contact, Profile
from app.infrastructure.db.orm_models import ProfileRow


class SqlProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID) -> Profile | None:
        row = await self._db.get(ProfileRow, session_id)
        return None if row is None else _profile(row)

    async def save(self, profile: Profile) -> None:
        row = await self._db.get(ProfileRow, profile.session_id)
        if row is None:
            row = ProfileRow(session_id=profile.session_id)
            self._db.add(row)
        row.enjoys = list(profile.enjoys)
        row.calms = list(profile.calms)
        row.avoid = list(profile.avoid)
        row.rhythm = profile.rhythm
        row.contacts = [_contact_json(c) for c in profile.contacts]
        row.caregiver_first_name = profile.caregiver_first_name
        row.updated_at = profile.updated_at


def _contact_json(contact: Contact) -> dict[str, Any]:
    return {"name": contact.name, "phone": contact.phone, "role": contact.role}


def _profile(row: ProfileRow) -> Profile:
    return Profile(
        row.session_id,
        tuple(row.enjoys),
        tuple(row.calms),
        tuple(row.avoid),
        row.rhythm,
        tuple(Contact(c["name"], c["phone"], c.get("role")) for c in row.contacts),
        row.caregiver_first_name,
        row.updated_at,
    )
