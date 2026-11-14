"""Base domain error: carries a code and data, never an HTTP status."""

from collections.abc import Mapping
from typing import Any


class DomainError(Exception):
    """Root of all domain and application errors; mapped to HTTP in presentation."""

    code: str = "domain_error"

    def __init__(self, message: str, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details or {})
