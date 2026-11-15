from datetime import date

import pytest

from app.domain.billing.fake_cards import evaluate_test_card, last4, normalize_card_number

TODAY = date(2026, 1, 5)


def _eval(number: str, month: int = 12, year: int = 2030, cvc: str = "123"):  # type: ignore[no-untyped-def]
    return evaluate_test_card(number, month, year, cvc, TODAY)


def test_4242_succeeds_with_any_future_expiry_and_three_or_four_digit_cvc() -> None:
    for cvc in ("123", "9999"):
        outcome = _eval("4242 4242 4242 4242", cvc=cvc)
        assert outcome.result == "succeeds" and not outcome.charge_fails_on_renewal
    assert _eval("4242424242424242", month=1, year=2026).result == "succeeds"  # this month
    assert _eval("4242424242424242", month=3, year=29).result == "succeeds"  # two-digit year


@pytest.mark.parametrize(
    ("number", "code", "decline_code"),
    [
        ("4000 0000 0000 0002", "card_declined", "generic_decline"),
        ("4000-0000-0000-9995", "card_declined", "insufficient_funds"),
        ("4000000000000069", "expired_card", "expired_card"),
        ("4000000000000127", "incorrect_cvc", "incorrect_cvc"),
        ("5555 5555 5555 4444", "card_declined", "generic_decline"),  # unknown number
        ("not a card", "card_declined", "generic_decline"),
    ],
)
def test_declined_cards_and_unknown_numbers(number: str, code: str, decline_code: str) -> None:
    outcome = _eval(number)
    assert (outcome.result, outcome.code, outcome.decline_code) == ("declined", code, decline_code)
    assert outcome.message


def test_past_expiry_is_expired_and_bad_cvc_is_incorrect_cvc() -> None:
    assert _eval("4242424242424242", month=12, year=2025).code == "expired_card"
    assert _eval("4242424242424242", cvc="12").code == "incorrect_cvc"
    assert _eval("4242424242424242", cvc="12a").code == "incorrect_cvc"


def test_card_that_fails_the_first_charge_is_accepted_but_flagged() -> None:
    outcome = _eval("4000 0000 0000 0341")
    assert outcome.result == "succeeds" and outcome.charge_fails_on_renewal


def test_three_d_secure_card_requires_action() -> None:
    assert _eval("4000 0025 0000 3155").result == "requires_action"


def test_number_helpers() -> None:
    assert normalize_card_number("4242 4242-4242 4242") == "4242424242424242"
    assert last4("4242 4242 4242 4242") == "4242"
