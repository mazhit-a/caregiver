"""Plan errors."""

from app.domain.shared.errors import DomainError


class NoPlan(DomainError):
    """The session has no built plan yet (the quiz was not completed).

    Code `payment_required` (HTTP 402) with `details["reason"] == "no_plan"`, the same shape
    the access gate uses, so the frontend routes the user back to the quiz.
    """

    code = "payment_required"

    def __init__(self) -> None:
        super().__init__("Finish the quiz to see your plan.", {"reason": "no_plan"})
