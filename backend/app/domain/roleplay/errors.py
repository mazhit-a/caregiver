from app.domain.shared.errors import DomainError


class InvalidReply(DomainError):
    code = "invalid_reply"


class RunNotFound(DomainError):
    """No such run for this session (also used for another session's run)."""

    code = "run_not_found"

    def __init__(self) -> None:
        super().__init__("We could not find this practice run.")


class RunFinished(DomainError):
    """The run was finished or stopped (crisis); no more turns."""

    code = "run_finished"

    def __init__(self) -> None:
        super().__init__("This practice run is over.")


class RoundMismatch(DomainError):
    """The client's round number is not the run's next round."""

    code = "round_mismatch"

    def __init__(self, expected: int, got: int) -> None:
        super().__init__("This is not the current round.", {"expected": expected, "got": got})


class TooManyPreviousTurns(DomainError):
    code = "too_many_previous_turns"

    def __init__(self, maximum: int) -> None:
        super().__init__("Too many previous turns.", {"max": maximum})


class TurnsMismatch(DomainError):
    """The phrases sent on finish do not match the turns scored in the run."""

    code = "turns_mismatch"

    def __init__(self, expected: int, got: int) -> None:
        super().__init__("The turns do not match this run.", {"expected": expected, "got": got})


class RateLimited(DomainError):
    """Too many role-play turns from one session in an hour; the UI offers the fallback."""

    code = "rate_limited"

    def __init__(self) -> None:
        super().__init__(
            "You've done a lot of practice this hour. Try the quick choices instead, "
            "or come back a little later."
        )


class InvalidCoachOutput(DomainError):
    """The model's output broke the contract (unknown flag or mood)."""

    code = "invalid_coach_output"
