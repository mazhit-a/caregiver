import logging

import pytest
from pydantic import ValidationError

from app.infrastructure.config import Settings


def _settings(**kwargs: str) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg]


def test_settings_reject_live_stripe_key() -> None:
    with pytest.raises(ValidationError):
        _settings(stripe_secret_key="sk_live_abc")


@pytest.mark.parametrize("key", ["sk_test_abc", "rk_test_abc"])
def test_settings_accept_test_stripe_keys(key: str) -> None:
    assert _settings(stripe_secret_key=key).stripe_secret_key == key


def test_settings_allow_missing_anthropic_key(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        s = _settings(anthropic_api_key="")
    assert s.anthropic_api_key == ""
    assert "ANTHROPIC_API_KEY" in caplog.text


def test_cors_origins_are_split() -> None:
    s = _settings(cors_origins="https://a.example, https://b.example")
    assert s.cors_origin_list == ["https://a.example", "https://b.example"]
