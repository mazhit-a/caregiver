"""Quiz errors."""

from app.domain.shared.errors import DomainError


class QuizLocked(DomainError):
    """The quiz can no longer be edited (the subscription has started)."""

    code = "quiz_locked"


class InvalidAnswer(DomainError):
    """The answer does not fit the question it was sent for."""

    code = "invalid_answer"


class UnknownQuestion(DomainError):
    """No answerable question with this id."""

    code = "unknown_question"


class QuizRuleError(DomainError):
    """A derived-tag condition in quiz.json that the quiz domain cannot read."""

    code = "quiz_rule_error"


class QuizIncomplete(DomainError):
    """Required questions are still unanswered; `details["questionIds"]` lists them."""

    code = "quiz_incomplete"
