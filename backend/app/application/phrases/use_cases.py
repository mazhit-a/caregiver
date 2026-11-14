"""Saved phrase use cases: save, list, delete (every row belongs to one session)."""

from uuid import UUID

from app.application.ports import Clock, IdGenerator, UnitOfWork
from app.domain.phrases.entities import MAX_PHRASES_PER_SESSION, SavedPhrase
from app.domain.phrases.errors import PhraseLimitReached, PhraseNotFound
from app.domain.session.entities import Session


class SavePhrase:
    def __init__(self, uow: UnitOfWork, ids: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    async def execute(
        self, session: Session, text: str, source: str, lesson_id: str | None
    ) -> SavedPhrase:
        phrase = SavedPhrase.create(
            self._ids.new_id(),
            session.id,
            text,
            source,
            lesson_id,
            session.app_now(self._clock.now()),
        )
        async with self._uow:
            if await self._uow.saved_phrases.count(session.id) >= MAX_PHRASES_PER_SESSION:
                raise PhraseLimitReached(MAX_PHRASES_PER_SESSION)
            await self._uow.saved_phrases.add(phrase)
            await self._uow.commit()
        return phrase


class ListPhrases:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, session: Session) -> list[SavedPhrase]:
        async with self._uow:
            return await self._uow.saved_phrases.list_for_session(session.id)


class DeletePhrase:
    """A phrase of another session is reported as not found, never as forbidden."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, session: Session, phrase_id: UUID) -> None:
        async with self._uow:
            if not await self._uow.saved_phrases.delete(session.id, phrase_id):
                raise PhraseNotFound(phrase_id)
            await self._uow.commit()
