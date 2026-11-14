"""Session token hashing: only the SHA-256 hash of a token is ever stored."""

import hashlib


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
