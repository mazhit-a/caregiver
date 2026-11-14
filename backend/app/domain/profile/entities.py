"""The non-medical profile ("Mom's page"): what she enjoys, what calms her, what to avoid, her
daily rhythm and who to call. No diagnosis, medication or health data by design (TASK 6.12).

The display name is NOT stored here: it lives in `sessions.display_name` (one source of truth,
read by placeholder rendering). Every field has a size limit; limits are enforced here and
mirrored in the request schema."""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.profile.errors import InvalidProfile

MAX_DISPLAY_NAME = 80  # matches the sessions.display_name column
MAX_CAREGIVER_NAME = 40
MAX_LIST_ITEMS = 10
MAX_ITEM_LENGTH = 80
MAX_RHYTHM_LENGTH = 500
MAX_CONTACTS = 5
MAX_CONTACT_NAME = 60
MAX_CONTACT_ROLE = 40
MAX_PHONE_LENGTH = 30
MIN_PHONE_DIGITS = 7
MAX_PHONE_DIGITS = 15

_PHONE_CHARS = re.compile(r"^\+?[0-9 ()\-.]+$")


@dataclass(frozen=True)
class Contact:
    name: str
    phone: str
    role: str | None = None


@dataclass(frozen=True)
class Profile:
    session_id: UUID
    enjoys: tuple[str, ...]
    calms: tuple[str, ...]
    avoid: tuple[str, ...]
    rhythm: str
    contacts: tuple[Contact, ...]
    caregiver_first_name: str | None
    updated_at: datetime

    @classmethod
    def create(
        cls,
        session_id: UUID,
        enjoys: Iterable[str],
        calms: Iterable[str],
        avoid: Iterable[str],
        rhythm: str,
        contacts: Sequence[Contact],
        caregiver_first_name: str | None,
        updated_at: datetime,
    ) -> "Profile":
        return cls(
            session_id,
            clean_list("enjoys", enjoys),
            clean_list("calms", calms),
            clean_list("avoid", avoid),
            clean_text("rhythm", rhythm, MAX_RHYTHM_LENGTH),
            clean_contacts(contacts),
            clean_optional("caregiverFirstName", caregiver_first_name, MAX_CAREGIVER_NAME),
            updated_at,
        )

    @classmethod
    def empty(cls, session_id: UUID, updated_at: datetime) -> "Profile":
        return cls(session_id, (), (), (), "", (), None, updated_at)


def clean_text(field: str, value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) > limit:
        raise InvalidProfile(f"{field} can be at most {limit} characters.", {"field": field})
    return cleaned


def clean_optional(field: str, value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return clean_text(field, value, limit) or None


def clean_display_name(value: str | None) -> str | None:
    return clean_optional("displayName", value, MAX_DISPLAY_NAME)


def clean_list(field: str, items: Iterable[str]) -> tuple[str, ...]:
    cleaned = tuple(clean_text(field, item, MAX_ITEM_LENGTH) for item in items)
    if len(cleaned) > MAX_LIST_ITEMS:
        raise InvalidProfile(f"{field} can have at most {MAX_LIST_ITEMS} items.", {"field": field})
    if any(not item for item in cleaned):
        raise InvalidProfile(f"{field} cannot contain empty items.", {"field": field})
    return cleaned


def clean_contacts(contacts: Sequence[Contact]) -> tuple[Contact, ...]:
    if len(contacts) > MAX_CONTACTS:
        raise InvalidProfile(
            f"contacts can have at most {MAX_CONTACTS} entries.", {"field": "contacts"}
        )
    return tuple(
        Contact(
            clean_text("contacts.name", c.name, MAX_CONTACT_NAME),
            clean_phone(c.phone),
            clean_optional("contacts.role", c.role, MAX_CONTACT_ROLE),
        )
        for c in contacts
    )


def clean_phone(value: str) -> str:
    """Sanity check only (digits, +, spaces, brackets, dashes, dots; 7 to 15 digits)."""
    phone = value.strip()
    digits = sum(ch.isdigit() for ch in phone)
    if (
        len(phone) > MAX_PHONE_LENGTH
        or not _PHONE_CHARS.match(phone)
        or not MIN_PHONE_DIGITS <= digits <= MAX_PHONE_DIGITS
    ):
        raise InvalidProfile(
            "A contact phone number does not look right.", {"field": "contacts.phone"}
        )
    return phone
