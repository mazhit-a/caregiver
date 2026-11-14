"""The care card: a public, revocable snapshot of a few whitelisted profile fields.

The snapshot is built ONLY by `build_snapshot` from an explicit whitelist (TASK 6.12): display
name, enjoys, calms, avoid, rhythm, contacts + helplines, chosen phrases, updated date and the
caregiver's first name. Quiz answers, diagnosis, medications, the visit sheet and every other
piece of data have no field here, so they cannot leak.

A card row is either live (`snapshot` set) or a tombstone (`revoked_at` set, snapshot and phrase
ids deleted). Republishing after a revoke creates a NEW card id; the old id stays a tombstone
(410) until the session is deleted (then 404)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.domain.profile.entities import Contact, Profile
from app.domain.safety.resources import CrisisResource

MIN_CARD_ID_LENGTH = 16
MAX_CARD_PHRASES = 10

SNAPSHOT_KEYS: frozenset[str] = frozenset(
    {
        "displayName",
        "enjoys",
        "calms",
        "avoid",
        "rhythm",
        "contacts",
        "helplines",
        "phrases",
        "updatedOn",
        "caregiverFirstName",
    }
)


@dataclass(frozen=True)
class Helpline:
    name: str
    phone: str
    description: str


@dataclass(frozen=True)
class CardSnapshot:
    display_name: str
    enjoys: tuple[str, ...]
    calms: tuple[str, ...]
    avoid: tuple[str, ...]
    rhythm: str
    contacts: tuple[Contact, ...]
    helplines: tuple[Helpline, ...]
    phrases: tuple[str, ...]
    updated_on: date
    caregiver_first_name: str | None

    def to_json(self) -> dict[str, Any]:
        """The stored form; its keys are exactly `SNAPSHOT_KEYS`."""
        return {
            "displayName": self.display_name,
            "enjoys": list(self.enjoys),
            "calms": list(self.calms),
            "avoid": list(self.avoid),
            "rhythm": self.rhythm,
            "contacts": [{"name": c.name, "phone": c.phone, "role": c.role} for c in self.contacts],
            "helplines": [
                {"name": h.name, "phone": h.phone, "description": h.description}
                for h in self.helplines
            ],
            "phrases": list(self.phrases),
            "updatedOn": self.updated_on.isoformat(),
            "caregiverFirstName": self.caregiver_first_name,
        }

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> "CardSnapshot":
        """Reads only whitelisted keys; anything else in the stored JSON is ignored."""
        return cls(
            display_name=raw["displayName"],
            enjoys=tuple(raw["enjoys"]),
            calms=tuple(raw["calms"]),
            avoid=tuple(raw["avoid"]),
            rhythm=raw["rhythm"],
            contacts=tuple(Contact(c["name"], c["phone"], c.get("role")) for c in raw["contacts"]),
            helplines=tuple(
                Helpline(h["name"], h["phone"], h["description"]) for h in raw["helplines"]
            ),
            phrases=tuple(raw["phrases"]),
            updated_on=date.fromisoformat(raw["updatedOn"]),
            caregiver_first_name=raw.get("caregiverFirstName"),
        )


def build_snapshot(
    display_name: str,
    profile: Profile | None,
    helplines: Sequence[CrisisResource],
    phrase_texts: Sequence[str],
    updated_on: date,
) -> CardSnapshot:
    """The only way to make a snapshot. `profile` None means nothing is filled in yet."""
    return CardSnapshot(
        display_name=display_name,
        enjoys=profile.enjoys if profile else (),
        calms=profile.calms if profile else (),
        avoid=profile.avoid if profile else (),
        rhythm=profile.rhythm if profile else "",
        contacts=profile.contacts if profile else (),
        helplines=tuple(Helpline(h.name, h.phone, h.description) for h in helplines),
        phrases=tuple(phrase_texts),
        updated_on=updated_on,
        caregiver_first_name=profile.caregiver_first_name if profile else None,
    )


@dataclass(frozen=True)
class CareCard:
    """`snapshot` is None exactly when the card is revoked (a tombstone)."""

    id: str
    session_id: UUID
    snapshot: CardSnapshot | None
    phrase_ids: tuple[UUID, ...]
    published_at: datetime
    updated_at: datetime
    revoked_at: datetime | None
    last_opened_at: datetime | None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @classmethod
    def publish(
        cls,
        card_id: str,
        session_id: UUID,
        snapshot: CardSnapshot,
        phrase_ids: Sequence[UUID],
        now: datetime,
    ) -> "CareCard":
        return cls(card_id, session_id, snapshot, tuple(phrase_ids), now, now, None, None)

    def resnapshot(
        self, snapshot: CardSnapshot, phrase_ids: Sequence[UUID], now: datetime
    ) -> "CareCard":
        """Update under the same id."""
        return CareCard(
            self.id,
            self.session_id,
            snapshot,
            tuple(phrase_ids),
            self.published_at,
            now,
            None,
            self.last_opened_at,
        )

    def revoke(self, now: datetime) -> "CareCard":
        """A tombstone: id, session and timestamps stay; the shared data is deleted."""
        return CareCard(
            self.id,
            self.session_id,
            None,
            (),
            self.published_at,
            self.updated_at,
            now,
            self.last_opened_at,
        )

    def opened(self, now: datetime) -> "CareCard":
        return CareCard(
            self.id,
            self.session_id,
            self.snapshot,
            self.phrase_ids,
            self.published_at,
            self.updated_at,
            self.revoked_at,
            now,
        )
