"""Care card errors: carry data, never HTTP codes."""

from app.domain.shared.errors import DomainError


class CardNotFound(DomainError):
    code = "card_not_found"

    def __init__(self) -> None:
        super().__init__("This card does not exist.")


class CardRevoked(DomainError):
    code = "card_revoked"

    def __init__(self) -> None:
        super().__init__("This card is no longer shared.")


class CardAlreadyPublished(DomainError):
    code = "card_already_published"

    def __init__(self) -> None:
        super().__init__("The care card is already published. Update it instead.")


class CardNotPublished(DomainError):
    code = "card_not_published"

    def __init__(self) -> None:
        super().__init__("There is no published care card.")


class InvalidCardPhrases(DomainError):
    code = "invalid_card_phrases"


class CardRateLimited(DomainError):
    code = "rate_limited"

    def __init__(self) -> None:
        super().__init__("Too many requests. Please try again in a minute.")
