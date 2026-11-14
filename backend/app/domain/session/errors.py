"""Session errors."""

from app.domain.shared.errors import DomainError


class InvalidTimezone(DomainError):
    code = "invalid_timezone"


class InvalidSessionToken(DomainError):
    """Missing, unknown or wrong session token."""

    code = "invalid_session_token"
