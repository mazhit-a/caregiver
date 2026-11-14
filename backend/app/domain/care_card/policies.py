"""Card status and the "new phrases" nudge count (pure; used by the care-card page and Today)."""

from collections.abc import Collection
from typing import Literal

from app.domain.care_card.entities import CareCard
from app.domain.phrases.entities import SavedPhrase
from app.domain.profile.entities import Profile

CardStatus = Literal["not_published", "published", "update_available", "revoked"]


def card_status(
    card: CareCard | None, profile: Profile | None, saved_phrases: Collection[SavedPhrase]
) -> CardStatus:
    """`update_available` when, since the card was last published or updated (`card.updated_at`,
    app time), the profile was saved again (`profile.updated_at > card.updated_at`) or a chosen
    phrase was deleted (a chosen id is no longer among the saved phrases). Phrases saved later
    but not chosen do not change the status; they only count toward `new_phrase_count`."""
    if card is None:
        return "not_published"
    if card.is_revoked:
        return "revoked"
    if profile is not None and profile.updated_at > card.updated_at:
        return "update_available"
    existing = {p.id for p in saved_phrases}
    if any(pid not in existing for pid in card.phrase_ids):
        return "update_available"
    return "published"


def new_phrase_count(card: CareCard | None, saved_phrases: Collection[SavedPhrase]) -> int:
    """Phrases saved after the card was last published or updated and not on it (0 when there is
    no live card)."""
    if card is None or card.is_revoked:
        return 0
    chosen = set(card.phrase_ids)
    return sum(1 for p in saved_phrases if p.id not in chosen and p.saved_at > card.updated_at)
