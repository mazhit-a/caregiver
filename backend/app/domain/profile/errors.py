"""Profile errors: carry data, never HTTP codes."""

from app.domain.shared.errors import DomainError


class InvalidProfile(DomainError):
    code = "invalid_profile"
