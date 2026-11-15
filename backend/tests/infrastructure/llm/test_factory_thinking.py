"""COACH_THINKING reaches the SDK call (the measured Haiku setting is thinking disabled)."""

import pytest

from app.infrastructure.config import Settings
from evals.client import production_config


def _settings(**kw: str) -> Settings:
    return Settings(anthropic_api_key="", **kw)


def test_default_is_haiku_with_thinking_disabled() -> None:
    s = _settings()
    assert s.coach_model == "claude-haiku-5-5"
    assert s.coach_thinking_param == {"type": "disabled"}
    assert production_config(s).thinking == {"type": "disabled"}


def test_empty_thinking_keeps_the_model_default() -> None:
    s = _settings(coach_thinking="")
    assert s.coach_thinking_param is None
    assert production_config(s).thinking is None


def test_unknown_thinking_value_is_refused_at_startup() -> None:
    with pytest.raises(ValueError, match="COACH_THINKING"):
        _settings(coach_thinking="enabled")
