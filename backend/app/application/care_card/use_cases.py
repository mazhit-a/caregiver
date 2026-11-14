"""Care card use cases. The snapshot is built only by `build_snapshot` (whitelist); nothing here
logs card or profile text."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports import Clock, ContentProvider, RateLimiter, TokenGenerator, UnitOfWork
from app.domain.care_card.entities import (
    MAX_CARD_PHRASES,
    MIN_CARD_ID_LENGTH,
    CardSnapshot,
    CareCard,
    build_snapshot,
)
from app.domain.care_card.errors import (
    CardAlreadyPublished,
    CardNotFound,
    CardNotPublished,
    CardRateLimited,
    CardRevoked,
    InvalidCardPhrases,
)
from app.domain.care_card.policies import CardStatus, card_status, new_phrase_count
from app.domain.phrases.entities import SavedPhrase
from app.domain.session.entities import Session

# Quiz recipient key whose label ("your loved one") is the default when no name is set.
DEFAULT_RECIPIENT_KEY = "other"


@dataclass(frozen=True)
class CareCardView:
    """`preview` is what publishing or updating now would share; `published` is what the link
    shows today (None unless live). `link_token` is the public id of a live card."""

    status: CardStatus
    link_token: str | None
    published: CardSnapshot | None
    preview: CardSnapshot
    chosen_phrase_ids: tuple[UUID, ...]
    available_phrases: tuple[SavedPhrase, ...]
    new_phrase_count: int
    published_at: datetime | None
    updated_at: datetime | None
    last_opened_at: datetime | None
    revoked_at: datetime | None


def _display_name(session: Session, content: ContentProvider) -> str:
    if session.display_name:
        return session.display_name
    return content.recipient_labels(session.recipient_key or DEFAULT_RECIPIENT_KEY).recipient


def _chosen(phrases: Sequence[SavedPhrase], phrase_ids: Sequence[UUID]) -> list[SavedPhrase]:
    """The chosen phrases in the chosen order; ids that are not the session's are rejected."""
    unique = list(dict.fromkeys(phrase_ids))
    if len(unique) > MAX_CARD_PHRASES:
        raise InvalidCardPhrases(
            f"A card can have at most {MAX_CARD_PHRASES} phrases.", {"max": MAX_CARD_PHRASES}
        )
    by_id = {p.id: p for p in phrases}
    if any(pid not in by_id for pid in unique):
        raise InvalidCardPhrases("One of the chosen phrases is not in your saved phrases.")
    return [by_id[pid] for pid in unique]


async def _snapshot(
    uow: UnitOfWork,
    content: ContentProvider,
    clock: Clock,
    session: Session,
    phrases: Sequence[SavedPhrase],
) -> CardSnapshot:
    profile = await uow.profiles.get(session.id)
    return build_snapshot(
        _display_name(session, content),
        profile,
        content.crisis_resources(),
        [p.text for p in phrases],
        session.app_today(clock.now()),
    )


class GetCareCard:
    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock

    async def execute(self, session: Session) -> CareCardView:
        async with self._uow:
            card = await self._uow.care_cards.get_current(session.id)
            profile = await self._uow.profiles.get(session.id)
            saved = await self._uow.saved_phrases.list_for_session(session.id)
            live = card if card is not None and not card.is_revoked else None
            chosen_ids = live.phrase_ids if live else ()
            existing = {p.id for p in saved}
            kept = [pid for pid in chosen_ids if pid in existing]
            preview = await _snapshot(
                self._uow,
                self._content,
                self._clock,
                session,
                _chosen(saved, kept),
            )
        return CareCardView(
            status=card_status(card, profile, saved),
            link_token=live.id if live else None,
            published=live.snapshot if live else None,
            preview=preview,
            chosen_phrase_ids=tuple(chosen_ids),
            available_phrases=tuple(saved),
            new_phrase_count=new_phrase_count(card, saved),
            published_at=card.published_at if card else None,
            updated_at=card.updated_at if card else None,
            last_opened_at=card.last_opened_at if card else None,
            revoked_at=card.revoked_at if card else None,
        )


class PublishCareCard:
    """Create a card with a new random id. After a revoke this is a NEW card (new id)."""

    def __init__(
        self,
        uow: UnitOfWork,
        content: ContentProvider,
        clock: Clock,
        tokens: TokenGenerator,
    ) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._tokens = tokens

    async def execute(self, session: Session, phrase_ids: Sequence[UUID]) -> CareCard:
        async with self._uow:
            current = await self._uow.care_cards.get_current(session.id)
            if current is not None and not current.is_revoked:
                raise CardAlreadyPublished()
            saved = await self._uow.saved_phrases.list_for_session(session.id)
            chosen = _chosen(saved, phrase_ids)
            snapshot = await _snapshot(self._uow, self._content, self._clock, session, chosen)
            card = CareCard.publish(
                _card_id(self._tokens),
                session.id,
                snapshot,
                [p.id for p in chosen],
                session.app_now(self._clock.now()),
            )
            await self._uow.care_cards.save(card)
            await self._uow.events.record(
                session.id, "card_published", {"phrases": len(chosen)}, card.published_at
            )
            await self._uow.commit()
        return card


def _card_id(tokens: TokenGenerator) -> str:
    token = tokens.new_token()
    if len(token) < MIN_CARD_ID_LENGTH:
        raise ValueError("The token generator returned a card id that is too short.")
    return token


class UpdateCareCard:
    """Re-snapshot the live card under the same id."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock

    async def execute(self, session: Session, phrase_ids: Sequence[UUID]) -> CareCard:
        async with self._uow:
            current = await self._uow.care_cards.get_current(session.id)
            if current is None or current.is_revoked:
                raise CardNotPublished()
            saved = await self._uow.saved_phrases.list_for_session(session.id)
            chosen = _chosen(saved, phrase_ids)
            snapshot = await _snapshot(self._uow, self._content, self._clock, session, chosen)
            card = current.resnapshot(
                snapshot, [p.id for p in chosen], session.app_now(self._clock.now())
            )
            await self._uow.care_cards.save(card)
            await self._uow.commit()
        return card


class RevokeCareCard:
    """Delete the snapshot data and keep a tombstone (id, session, timestamps)."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session) -> None:
        async with self._uow:
            current = await self._uow.care_cards.get_current(session.id)
            if current is None or current.is_revoked:
                raise CardNotPublished()
            await self._uow.care_cards.save(current.revoke(session.app_now(self._clock.now())))
            await self._uow.commit()


class GetPublicCard:
    """No session. Unknown id -> CardNotFound; revoked -> CardRevoked; else the snapshot, and
    `last_opened_at` is recorded (real time: there is no session offset here)."""

    def __init__(self, uow: UnitOfWork, clock: Clock, limiter: RateLimiter) -> None:
        self._uow = uow
        self._clock = clock
        self._limiter = limiter

    async def execute(self, card_id: str, client_key: str) -> CardSnapshot:
        now = self._clock.now()
        if not await self._limiter.allow(client_key, now):
            raise CardRateLimited()
        async with self._uow:
            card = await self._uow.care_cards.get(card_id)
            if card is None:
                raise CardNotFound()
            if card.is_revoked or card.snapshot is None:
                raise CardRevoked()
            await self._uow.care_cards.save(card.opened(now))
            await self._uow.commit()
        return card.snapshot
