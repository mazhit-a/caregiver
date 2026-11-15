import logging

import pytest

from app.infrastructure.logging import QUIET_LOGGERS, RedactingFilter, configure_logging, redact

CARD = "Zk3-card_id-SECRET0123456789"


def test_redact_hides_card_ids_in_paths_and_keeps_the_rest() -> None:
    assert redact(f"GET /api/cards/{CARD} -> 200") == "GET /api/cards/[redacted] -> 200"
    assert redact("GET /api/lessons/m1_l1 -> 200") == "GET /api/lessons/m1_l1 -> 200"


@pytest.mark.parametrize(
    "secret",
    [
        "sk-ant-" + "api03-abcdefghijklmnop",
        "sk_test_" + "A" * 24,
        "sk_live_" + "A" * 24,
        "whsec_" + "B" * 24,
    ],
)
def test_redact_hides_api_keys(secret: str) -> None:
    assert secret not in redact(f"key is {secret} ok")


def test_redact_hides_a_session_token_header() -> None:
    assert "tok123" not in redact("headers {'X-Session-Token': 'tok123'}")
    assert "tok123" not in redact("x-session-token=tok123")


def test_filter_redacts_args_not_just_the_template(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.request")
    configure_logging()
    configure_logging()  # idempotent: one filter only
    assert sum(isinstance(f, RedactingFilter) for f in logger.filters) == 1
    caplog.set_level(logging.INFO)
    logger.info("GET %s", f"/api/cards/{CARD}")
    assert CARD not in caplog.text


def test_noisy_libraries_are_pinned_to_warning() -> None:
    configure_logging()
    for name in QUIET_LOGGERS:
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING, name
    assert logging.getLogger("sqlalchemy.engine").getEffectiveLevel() >= logging.WARNING


def test_redact_hides_fake_checkout_ids_in_every_path() -> None:
    secret = "cs_fake_Qx9-abc_DEF0123456789"
    for path in (
        f"POST /api/fake-stripe/checkout/{secret}/pay -> 200",
        f"GET /api/billing/checkout/{secret} -> 200",
        f"GET /fake-checkout/{secret}",
    ):
        assert secret not in redact(path)
    assert redact(f"GET /api/fake-stripe/checkout/{secret}") == (
        "GET /api/fake-stripe/checkout/cs_fake_[redacted]"
    )
