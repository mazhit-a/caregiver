from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.phrases.entities import RECAP_PHRASE_MARKER, SavedPhrase, fill_recap
from app.domain.phrases.errors import InvalidPhrase

NOW = datetime(2026, 1, 5, tzinfo=UTC)


def test_phrase_is_trimmed_and_limited() -> None:
    phrase = SavedPhrase.create(uuid4(), uuid4(), "  It's okay.  ", "gift", None, NOW)
    assert phrase.text == "It's okay."
    for bad in ("   ", "x" * 301):
        with pytest.raises(InvalidPhrase):
            SavedPhrase.create(uuid4(), uuid4(), bad, "gift", None, NOW)
    with pytest.raises(InvalidPhrase):
        SavedPhrase.create(uuid4(), uuid4(), "ok", "elsewhere", None, NOW)


def test_fill_recap_with_phrase_and_without() -> None:
    text = f'Last time you practiced. Your phrase was: "{RECAP_PHRASE_MARKER}".'
    assert (
        fill_recap(text, "I am here.") == 'Last time you practiced. Your phrase was: "I am here.".'
    )
    assert fill_recap(text, None) == "Last time you practiced."
