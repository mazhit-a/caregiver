"""Saved phrase errors: carry data, never HTTP codes."""

from uuid import UUID

from app.domain.shared.errors import DomainError


class InvalidPhrase(DomainError):
    code = "invalid_phrase"


class PhraseLimitReached(DomainError):
    code = "phrase_limit_reached"

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"You have saved {limit} phrases, which is the most we can keep. "
            "Remove one to save another.",
            {"limit": limit},
        )


class PhraseNotFound(DomainError):
    code = "phrase_not_found"

    def __init__(self, phrase_id: UUID) -> None:
        super().__init__("We could not find this phrase.", {"phraseId": str(phrase_id)})
