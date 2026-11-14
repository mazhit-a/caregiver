"""Session use cases: create an anonymous session, resolve one from its token."""

from datetime import timedelta

from app.application.demo.renewals import RollDemoRenewals
from app.application.ports import Clock, IdGenerator, TokenGenerator, UnitOfWork
from app.application.session.dto import CreatedSession
from app.domain.session.entities import DEFAULT_TIMEZONE, Session, validate_timezone
from app.domain.session.errors import InvalidSessionToken
from app.domain.session.tokens import hash_token


class CreateSession:
    def __init__(
        self, uow: UnitOfWork, tokens: TokenGenerator, ids: IdGenerator, clock: Clock
    ) -> None:
        self._uow = uow
        self._tokens = tokens
        self._ids = ids
        self._clock = clock

    async def execute(self, timezone: str | None) -> CreatedSession:
        zone = timezone or DEFAULT_TIMEZONE
        validate_timezone(zone)
        token = self._tokens.new_token()
        now = self._clock.now()
        session = Session(
            id=self._ids.new_id(),
            token_hash=hash_token(token),
            timezone=zone,
            clock_offset=timedelta(0),
            created_at=now,
            last_seen_at=now,
        )
        async with self._uow:
            await self._uow.sessions.add(session)
            await self._uow.commit()
        return CreatedSession(token=token, session=session)


class ResolveSession:
    """Find the session for a token, touch last_seen_at, record the app day, roll demo renewals."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, roll_renewals: RollDemoRenewals | None = None
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._roll_renewals = roll_renewals

    async def execute(self, token: str | None) -> Session:
        if not token:
            raise InvalidSessionToken("A valid session token is required.")
        real_now = self._clock.now()
        async with self._uow:
            session = await self._uow.sessions.get_by_token_hash(hash_token(token))
            if session is None:
                raise InvalidSessionToken("A valid session token is required.")
            session.touch(real_now)
            await self._uow.sessions.save(session)
            await self._uow.active_days.record(session.id, session.app_today(real_now))
            if self._roll_renewals is not None:
                await self._roll_renewals.execute(session, session.app_now(real_now))
            await self._uow.commit()
        return session
