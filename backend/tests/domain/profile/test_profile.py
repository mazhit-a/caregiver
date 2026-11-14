from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.profile.entities import (
    MAX_CONTACTS,
    MAX_ITEM_LENGTH,
    MAX_LIST_ITEMS,
    MAX_RHYTHM_LENGTH,
    Contact,
    Profile,
    clean_phone,
)
from app.domain.profile.errors import InvalidProfile

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def make(**changes: object) -> Profile:
    args: dict[str, object] = {
        "enjoys": ["music"],
        "calms": ["tea"],
        "avoid": ["crowds"],
        "rhythm": "Up at 7",
        "contacts": [],
        "caregiver_first_name": None,
    }
    return Profile.create(uuid4(), updated_at=NOW, **{**args, **changes})  # type: ignore[arg-type]


def test_whitespace_is_collapsed_and_blank_caregiver_name_becomes_none() -> None:
    p = make(enjoys=["  old   songs "], caregiver_first_name="   ")
    assert p.enjoys == ("old songs",) and p.caregiver_first_name is None


@pytest.mark.parametrize(
    "changes",
    [
        {"enjoys": ["x"] * (MAX_LIST_ITEMS + 1)},
        {"calms": ["x" * (MAX_ITEM_LENGTH + 1)]},
        {"avoid": [" "]},
        {"rhythm": "x" * (MAX_RHYTHM_LENGTH + 1)},
        {"contacts": [Contact("A", "555 123 4567")] * (MAX_CONTACTS + 1)},
        {"caregiver_first_name": "x" * 41},
    ],
)
def test_limits_are_enforced(changes: dict[str, object]) -> None:
    with pytest.raises(InvalidProfile):
        make(**changes)


@pytest.mark.parametrize("phone", ["555-123-4567", "+1 (555) 123 4567", "020 7946 0958"])
def test_phone_sanity_accepts_common_formats(phone: str) -> None:
    assert clean_phone(phone) == phone


@pytest.mark.parametrize("phone", ["call me", "12", "555-CALL-NOW", "1" * 20, "+" + "1" * 30])
def test_phone_sanity_rejects_nonsense(phone: str) -> None:
    with pytest.raises(InvalidProfile):
        clean_phone(phone)
