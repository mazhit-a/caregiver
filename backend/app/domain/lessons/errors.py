"""Lesson errors: carry data, never HTTP codes."""

from datetime import date

from app.domain.shared.errors import DomainError


class LessonLocked(DomainError):
    """The lesson exists in the plan but its unlock date has not arrived."""

    code = "lesson_locked"

    def __init__(self, lesson_id: str, unlock_on: date) -> None:
        super().__init__(
            "This lesson is not unlocked yet.",
            {"lesson": lesson_id, "unlockOn": unlock_on.isoformat()},
        )
        self.unlock_on = unlock_on


class UnknownLesson(DomainError):
    """No lesson with this id exists in the plan or the content."""

    code = "unknown_lesson"

    def __init__(self, lesson_id: str) -> None:
        super().__init__("We could not find this lesson.", {"lesson": lesson_id})


class LessonNotAvailable(DomainError):
    """The lesson is planned but not built yet (or not part of this plan)."""

    code = "lesson_not_available"

    def __init__(self, lesson_id: str) -> None:
        super().__init__("This lesson is not available yet.", {"lesson": lesson_id})


class LessonContentError(DomainError):
    """A lesson file's variant map does not cover the chosen variant (an authoring error)."""

    code = "lesson_content_error"


class UnknownScreen(DomainError):
    """The screen id is not part of the lesson as the learner currently sees it."""

    code = "unknown_screen"

    def __init__(self, lesson_id: str, screen_id: str) -> None:
        super().__init__(
            "This screen is not part of the lesson.", {"lesson": lesson_id, "screen": screen_id}
        )


class InvalidScreenAnswer(DomainError):
    """The answer does not fit the screen (wrong value type, option not on the screen, or a
    screen type that takes no answer)."""

    code = "invalid_screen_answer"

    def __init__(self, screen_id: str, reason: str) -> None:
        super().__init__(
            "This answer does not fit the screen.", {"screen": screen_id, "reason": reason}
        )


class InvalidLessonStep(DomainError):
    """The step is not a screen index of the lesson as the learner currently sees it."""

    code = "invalid_lesson_step"

    def __init__(self, lesson_id: str, step: int, screen_count: int) -> None:
        super().__init__(
            "This step is not part of the lesson.",
            {"lesson": lesson_id, "step": step, "screenCount": screen_count},
        )
