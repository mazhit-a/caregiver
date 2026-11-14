"""The Anthropic SDK logs full request bodies (including the caregiver's reply) at DEBUG.

Importing the coach adapter must keep that logger at WARNING or above.
"""

import logging

import app.infrastructure.llm.anthropic_coach  # noqa: F401  (import has the side effect under test)


def test_anthropic_sdk_logger_never_emits_debug_request_bodies() -> None:
    assert logging.getLogger("anthropic").level >= logging.WARNING
    assert logging.getLogger("anthropic._base_client").getEffectiveLevel() >= logging.WARNING
