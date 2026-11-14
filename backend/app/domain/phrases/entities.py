"""The saved phrase entity and the recap wording rule."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from app.domain.phrases.errors import InvalidPhrase

PhraseSource = Literal["scenario", "roleplay", "gift"]
PHRASE_SOURCES: tuple[str, ...] = ("scenario", "roleplay", "gift")
MAX_PHRASE_LENGTH = 300
MAX_PHRASES_PER_SESSION = 50
MAX_LESSON_ID_LENGTH = 64

# Stands in for the user's phrase while the recap is rendered by the content provider.
RECAP_PHRASE_MARKER = "\x00phrase\x00"
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class SavedPhrase:
    id: UUID
    session_id: UUID
    text: str
    source: PhraseSource
    lesson_id: str | None
    saved_at: datetime

    @classmethod
    def create(
        cls,
        id: UUID,
        session_id: UUID,
        text: str,
        source: str,
        lesson_id: str | None,
        saved_at: datetime,
    ) -> "SavedPhrase":
        cleaned = text.strip()
        if not cleaned:
            raise InvalidPhrase("The phrase cannot be empty.")
        if len(cleaned) > MAX_PHRASE_LENGTH:
            raise InvalidPhrase(
                f"A phrase can be at most {MAX_PHRASE_LENGTH} characters.",
                {"max": MAX_PHRASE_LENGTH},
            )
        if source not in PHRASE_SOURCES:
            raise InvalidPhrase("The phrase source is not valid.", {"allowed": PHRASE_SOURCES})
        if lesson_id is not None and not 0 < len(lesson_id) <= MAX_LESSON_ID_LENGTH:
            raise InvalidPhrase("The lesson id is not valid.")
        return cls(id, session_id, cleaned, cast(PhraseSource, source), lesson_id, saved_at)


def fill_recap(rendered: str, phrase: str | None) -> str:
    """The recap text with the user's phrase; without one, the sentence that quotes the phrase is
    dropped and the rest of the lesson's own recap text is used."""
    if phrase is not None:
        return rendered.replace(RECAP_PHRASE_MARKER, phrase)
    kept = [s for s in _SENTENCE_BREAK.split(rendered) if RECAP_PHRASE_MARKER not in s]
    return " ".join(kept).strip()
