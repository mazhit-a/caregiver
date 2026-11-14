"""Mom's page: read and replace the non-medical profile. The display name is kept in
`sessions.display_name` (so placeholder rendering reads it); the rest in the `profiles` row.
Profile text is free-form family data: nothing here logs it."""

from dataclasses import dataclass
from datetime import datetime

from app.application.ports import Clock, UnitOfWork
from app.domain.profile.entities import Contact, Profile, clean_display_name
from app.domain.session.entities import Session


@dataclass(frozen=True)
class ProfileView:
    """`display_name` is the onboarding name or None (then lessons use the quiz label)."""

    display_name: str | None
    profile: Profile
    exists: bool


@dataclass(frozen=True)
class ProfileInput:
    display_name: str | None
    enjoys: tuple[str, ...]
    calms: tuple[str, ...]
    avoid: tuple[str, ...]
    rhythm: str
    contacts: tuple[Contact, ...]
    caregiver_first_name: str | None


class GetProfile:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session) -> ProfileView:
        async with self._uow:
            stored = await self._uow.profiles.get(session.id)
        if stored is None:
            now = _now(session, self._clock)
            return ProfileView(session.display_name, Profile.empty(session.id, now), False)
        return ProfileView(session.display_name, stored, True)


class UpdateProfile:
    """Replace the whole profile (PUT). Also sets the session's display name."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session, data: ProfileInput) -> ProfileView:
        display_name = clean_display_name(data.display_name)
        profile = Profile.create(
            session.id,
            data.enjoys,
            data.calms,
            data.avoid,
            data.rhythm,
            data.contacts,
            data.caregiver_first_name,
            _now(session, self._clock),
        )
        session.display_name = display_name
        async with self._uow:
            await self._uow.profiles.save(profile)
            await self._uow.sessions.save(session)
            await self._uow.commit()
        return ProfileView(display_name, profile, True)


def _now(session: Session, clock: Clock) -> datetime:
    return session.app_now(clock.now())
