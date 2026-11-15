"""Stripe's documented test cards, as the in-app fake checkout understands them.

Pure rules, no I/O: https://docs.stripe.com/testing. The wording of the decline messages mimics
Stripe's own error messages (it is simulated provider output, not product copy). Card numbers are
only ever read here; nothing stores or logs them.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

CardResult = Literal["succeeds", "requires_action", "declined"]

SUCCESS_CARD = "4242424242424242"
CHARGE_FAILS_LATER_CARD = "4000000000000341"  # attaches fine; the first renewal charge fails
THREE_D_SECURE_CARD = "4000002500003155"

_GENERIC_DECLINE = ("card_declined", "generic_decline", "Your card was declined.")
# number -> (code, declineCode, message)
_DECLINED_CARDS: dict[str, tuple[str, str, str]] = {
    "4000000000000002": ("card_declined", "generic_decline", "Your card was declined."),
    "4000000000009995": (
        "card_declined",
        "insufficient_funds",
        "Your card has insufficient funds.",
    ),
    "4000000000000069": ("expired_card", "expired_card", "Your card has expired."),
    "4000000000000127": (
        "incorrect_cvc",
        "incorrect_cvc",
        "Your card's security code is incorrect.",
    ),
}
_EXPIRED = ("expired_card", "expired_card", "Your card has expired.")
_BAD_CVC = ("incorrect_cvc", "incorrect_cvc", "Your card's security code is incorrect.")


@dataclass(frozen=True)
class CardOutcome:
    result: CardResult
    code: str = ""
    decline_code: str = ""
    message: str = ""
    charge_fails_on_renewal: bool = False


def normalize_card_number(raw: str) -> str:
    """Digits only: spaces and dashes are ignored, as card forms do."""
    return "".join(ch for ch in raw if ch.isdigit())


def last4(raw: str) -> str:
    return normalize_card_number(raw)[-4:]


def _declined(entry: tuple[str, str, str]) -> CardOutcome:
    code, decline_code, message = entry
    return CardOutcome("declined", code, decline_code, message)


def _expired(exp_month: int, exp_year: int, today: date) -> bool:
    year = exp_year + 2000 if exp_year < 100 else exp_year
    return (year, exp_month) < (today.year, today.month)


def evaluate_test_card(
    number: str, exp_month: int, exp_year: int, cvc: str, today: date
) -> CardOutcome:
    """What the fake checkout does with this card.

    Table cards behave as documented. Any other number is declined (`generic_decline`); 4242 and
    the 0341 / 3155 cards accept any future expiry and any 3 or 4 digit CVC.
    """
    digits = normalize_card_number(number)
    fixed = _DECLINED_CARDS.get(digits)
    if fixed is not None:
        return _declined(fixed)
    if digits not in (SUCCESS_CARD, CHARGE_FAILS_LATER_CARD, THREE_D_SECURE_CARD):
        return _declined(_GENERIC_DECLINE)
    if _expired(exp_month, exp_year, today):
        return _declined(_EXPIRED)
    if not (cvc.isdigit() and len(cvc) in (3, 4)):
        return _declined(_BAD_CVC)
    if digits == THREE_D_SECURE_CARD:
        return CardOutcome("requires_action")
    return CardOutcome("succeeds", charge_fails_on_renewal=digits == CHARGE_FAILS_LATER_CARD)
