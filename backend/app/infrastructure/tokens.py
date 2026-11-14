"""Random adapters: session tokens and internal ids."""

import secrets
import uuid
from uuid import UUID

TOKEN_BYTES = 32


class SecretsTokenGenerator:
    """URL-safe tokens from 32 random bytes (43 characters)."""

    def new_token(self) -> str:
        return secrets.token_urlsafe(TOKEN_BYTES)


class UuidGenerator:
    def new_id(self) -> UUID:
        return uuid.uuid4()
