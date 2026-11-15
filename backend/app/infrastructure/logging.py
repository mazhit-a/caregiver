"""Logging hygiene: redaction of bearer secrets in log text and quiet third-party loggers.

Card ids (`/api/cards/{id}`) are bearer secrets: whoever holds the id can read the card. Session
tokens travel in a header and API keys in the environment; none of them may reach a log line.
`redact` is the single place that knows the patterns; the access log and `RedactingFilter` use it.
"""

import logging
import re

# (pattern, replacement). Order does not matter, the patterns do not overlap.
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(/api/cards/)[^\s/?#\"']+"), r"\1[redacted]"),
    (re.compile(r"(?i)(x-session-token['\"]?\s*[:=]\s*['\"]?)[^\s,'\"}]+"), r"\1[redacted]"),
    (re.compile(r"\bcs_fake_[A-Za-z0-9_\-]+"), "cs_fake_[redacted]"),  # fake checkout ids
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]+"), "[redacted-key]"),
    (re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]+"), "[redacted-key]"),
    (re.compile(r"\bwhsec_[A-Za-z0-9]+"), "[redacted-key]"),
)

# Libraries that log bodies, headers, URLs or SQL parameters at DEBUG/INFO stay at WARNING.
QUIET_LOGGERS = ("anthropic", "httpx", "httpcore", "stripe", "sqlalchemy", "asyncpg")


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_path(path: str) -> str:
    """The path as it may appear in a log: card ids replaced."""
    return redact(path)


class RedactingFilter(logging.Filter):
    """Redacts the formatted message of every record that passes (secrets in args included)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        cleaned = redact(message)
        if cleaned != message:
            record.msg = cleaned
            record.args = None
        return True


def configure_logging() -> None:
    """Idempotent: pin noisy libraries to WARNING and redact the access-style loggers."""
    for name in QUIET_LOGGERS:
        logger = logging.getLogger(name)
        logger.setLevel(max(logger.level, logging.WARNING))
    for name in ("app.request", "uvicorn.access", "uvicorn.error", "app.error"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactingFilter) for f in logger.filters):
            logger.addFilter(RedactingFilter())
