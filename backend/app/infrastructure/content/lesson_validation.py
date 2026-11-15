"""Cross-field checks of one lesson file that the Pydantic models cannot express.

Each problem is a `(field path, message)` pair; the loader turns them into a `ContentLoadError`
that names the file and the path, so an authoring gap is found at startup, not by a learner.
"""

from collections.abc import Iterator, Mapping

from app.infrastructure.content.schemas import (
    BuilderScreen,
    ContentScreen,
    IntroScreen,
    LessonFile,
    LessonScreen,
    PlanScreen,
    QuizScreen,
    RoleplayScreen,
    ScenarioScreen,
    SetupScreen,
)

Problem = tuple[str, str]
VERDICTS = frozenset({"best", "okay", "try_again"})


def validate_lesson(lesson: LessonFile) -> list[Problem]:
    """All problems of a lesson, in file order; empty when it is valid."""
    return [
        *_unique_ids(lesson),
        *_references(lesson),
        *_setup_position(lesson),
        *_variant_coverage(lesson),
        *_options(lesson),
        *_verdicts(lesson),
        *_timing(lesson),
    ]


def _unique_ids(lesson: LessonFile) -> Iterator[Problem]:
    seen: dict[str, int] = {}
    for index, screen in enumerate(lesson.screens):
        if screen.id in seen:
            yield f"screens.{index}.id", f"duplicate screen id '{screen.id}'"
        seen.setdefault(screen.id, index)
    fallback_ids: set[str] = set()
    for index, fallback in enumerate(lesson.fallback_scenarios):
        if fallback.id in fallback_ids:
            yield f"fallbackScenarios.{index}.id", f"duplicate fallback id '{fallback.id}'"
        fallback_ids.add(fallback.id)


def _references(lesson: LessonFile) -> Iterator[Problem]:
    screen_ids = {screen.id for screen in lesson.screens}
    fallback_ids = {fallback.id for fallback in lesson.fallback_scenarios}
    for index, screen in enumerate(lesson.screens):
        if isinstance(screen, PlanScreen) and screen.if_then.reset_from not in screen_ids:
            yield (
                f"screens.{index}.ifThen.resetFrom",
                f"no screen with id '{screen.if_then.reset_from}'",
            )
        if isinstance(screen, RoleplayScreen):
            for number, ref in enumerate(screen.fallback_scenarios):
                if ref not in fallback_ids:
                    yield (
                        f"screens.{index}.fallbackScenarios.{number}",
                        f"no fallback scenario with id '{ref}'",
                    )


def _is_setup(screen: LessonScreen) -> bool:
    return isinstance(screen, SetupScreen)


def _setup_position(lesson: LessonFile) -> Iterator[Problem]:
    setups = [i for i, screen in enumerate(lesson.screens) if _is_setup(screen)]
    for index in setups[1:]:
        yield f"screens.{index}", "a lesson has at most one setup screen"
    if not setups:
        return
    for index, screen in enumerate(lesson.screens):
        if index < setups[0] and _by_variant_blocks(screen):
            yield f"screens.{index}", "by-variant content must come after the setup screen"


def _by_variant_blocks(
    screen: LessonScreen,
) -> list[tuple[str, Mapping[str, object], Mapping[str, str]]]:
    """`(field, by-variant mapping, variant map)` of every block a variant selects."""
    if isinstance(screen, ScenarioScreen):
        return [
            ("setupByVariant", screen.setup_by_variant, screen.setup_variant_map),
            ("lineByVariant", screen.line_by_variant, screen.setup_variant_map),
            ("optionsByVariant", screen.options_by_variant, screen.options_variant_map),
        ]
    if isinstance(screen, ContentScreen) and screen.body_by_variant is not None:
        return [("bodyByVariant", screen.body_by_variant, screen.body_variant_map or {})]
    if isinstance(screen, RoleplayScreen):
        return [("roundsByVariant", screen.rounds_by_variant, screen.rounds_variant_map)]
    if isinstance(screen, PlanScreen):
        return [
            ("ifThen.cueByVariant", screen.if_then.cue_by_variant, screen.if_then.cue_variant_map),
            ("doNow.byVariant", screen.do_now.by_variant, {}),
        ]
    return []


def _variant_coverage(lesson: LessonFile) -> Iterator[Problem]:
    variants = lesson.variant_ids()
    if not variants:
        return  # a lesson without a setup screen is read without a variant (checked at render)
    for index, screen in enumerate(lesson.screens):
        for field, options, variant_map in _by_variant_blocks(screen):
            for variant in variants:
                key = variant_map.get(variant, variant)
                if key not in options:
                    yield (
                        f"screens.{index}.{field}",
                        f"variant '{variant}' resolves to '{key}', which has no entry",
                    )


def _correct_count(options: list[bool]) -> int:
    return sum(1 for correct in options if correct)


def _options(lesson: LessonFile) -> Iterator[Problem]:
    for index, screen in enumerate(lesson.screens):
        if (
            isinstance(screen, QuizScreen)
            and _correct_count([o.correct for o in screen.options]) != 1
        ):
            yield f"screens.{index}.options", "a quiz needs exactly one correct option"
        if isinstance(screen, BuilderScreen):
            for number, group in enumerate(screen.groups):
                if _correct_count([o.correct for o in group.options]) != 1:
                    yield (
                        f"screens.{index}.groups.{number}.options",
                        "a builder group needs exactly one correct option",
                    )


def _verdicts(lesson: LessonFile) -> Iterator[Problem]:
    for index, screen in enumerate(lesson.screens):
        if not isinstance(screen, ScenarioScreen):
            continue
        for variant, options in screen.options_by_variant.items():
            for number, option in enumerate(options):
                if option.verdict not in VERDICTS:
                    yield (
                        f"screens.{index}.optionsByVariant.{variant}.{number}.verdict",
                        f"'{option.verdict}' is not one of best, okay, try_again",
                    )
    for index, fallback in enumerate(lesson.fallback_scenarios):
        for number, answer in enumerate(fallback.answers):
            if answer.verdict not in VERDICTS:
                yield (
                    f"fallbackScenarios.{index}.answers.{number}.verdict",
                    f"'{answer.verdict}' is not one of best, okay, try_again",
                )


def _timing(lesson: LessonFile) -> Iterator[Problem]:
    for index, screen in enumerate(lesson.screens):
        if isinstance(screen, IntroScreen) and screen.minutes != lesson.minutes:
            yield (
                f"screens.{index}.minutes",
                f"intro says {screen.minutes} minutes, the lesson says {lesson.minutes}",
            )
    seconds = [screen.sec for screen in lesson.screens]
    if all(sec is not None for sec in seconds):
        total = sum(sec for sec in seconds if sec is not None)
        if round(total / 60) != lesson.minutes:
            yield "minutes", f"screens add up to {total} s, which is not {lesson.minutes} minutes"
