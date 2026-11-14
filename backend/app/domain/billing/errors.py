"""Billing errors."""

from typing import ClassVar, Literal

from app.domain.shared.errors import DomainError

AccessReason = Literal["no_plan", "no_subscription", "past_due", "ended"]


class AccessDenied(DomainError):
    """The subscription does not allow access to app endpoints.

    Code `payment_required` (HTTP 402) with `details["reason"]`, the same shape as `NoPlan`, so
    the frontend routes to the quiz, the paywall, an "update card" message or the exit screen.
    """

    code = "payment_required"

    _MESSAGES: ClassVar[dict[str, str]] = {
        "no_plan": "Finish the quiz to see your plan.",
        "no_subscription": "Start your subscription to continue.",
        "past_due": "Your last payment did not go through. Please update your card.",
        "ended": "Your subscription has ended.",
    }

    def __init__(self, reason: AccessReason) -> None:
        super().__init__(self._MESSAGES[reason], {"reason": reason})
        self.reason: AccessReason = reason


class InvalidTransition(DomainError):
    """The status change is not allowed by the subscription state machine."""

    code = "invalid_transition"


class ConsentRequired(DomainError):
    """A subscription cannot start without the auto-renew consent."""

    code = "consent_required"

    def __init__(self) -> None:
        super().__init__("Please confirm the auto-renewal terms to continue.")


class AlreadySubscribed(DomainError):
    """The session already has a subscription that is not `none`."""

    code = "already_subscribed"

    def __init__(self) -> None:
        super().__init__("You already have a subscription.")


class UnknownPlan(DomainError):
    """The plan id is not in pricing.json."""

    code = "unknown_plan"
