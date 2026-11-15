"""Checks on the real lesson files (Module 1). The wording is reviewed by the content owner;
these tests only guard shape, length and a few words that must never appear."""

import re
from pathlib import Path

import pytest

from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS, render_lesson
from app.infrastructure.content.loader import load_content
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.content.schemas import (
    LearnScreen,
    LessonFile,
    PhrasesReviewScreen,
    RoleplayScreen,
    ScenarioScreen,
)

REAL_CONTENT = Path(__file__).resolve().parents[4] / "content"
BUNDLE = load_content(REAL_CONTENT)
LESSONS: dict[str, LessonFile] = dict(BUNDLE.lessons)
NEW_LESSONS = ["m1_l2", "m1_l3", "m1_l4", "m1_l5"]  # drafts in the old 9-screen schema
RECIPIENT_KEYS = ["mom", "dad", "both", "in_law", "other"]
VARIANTS = ["in_person", "phone", "both", "not_yet"]
BLANKS = dict.fromkeys(RUNTIME_PLACEHOLDERS, "")
BUILT_IN_RULES = {
    lesson.id for module in BUNDLE.plan_rules.modules for lesson in module.lessons if lesson.built
}

# Small list, on purpose: price per day, countdowns, the word "patient", medical/legal advice.
BANNED = [
    r"\bpatients?\b",
    r"\bper day\b",
    r"\ba day\b",
    r"[$€£]\s?\d",
    r"\bcountdown\b",
    r"\b(hurry|act now|limited time|last chance|running out)\b",
    r"\bdays? left\b",
    r"\b(you should|you must|always) (take|give|stop)\b",
    r"\b\d+\s?(mg|ml)\b",
    r"\b(dose|dosage|prescri\w+|medication|diagnos\w+)\b",
    r"\b(lawyer|attorney|sue|lawsuit|legal advice|power of attorney)\b",
]


def _strings(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [t for item in node for t in _strings(item)]
    if isinstance(node, dict):
        return [t for value in node.values() for t in _strings(value)]
    return []


def _words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _lesson_text(lesson: LessonFile) -> list[str]:
    data = lesson.model_dump(by_alias=True, mode="json", exclude_none=True)
    data.pop("notes", None)  # authoring notes are not shown to the learner
    return _strings(data)


def test_lesson_passes_content_schema() -> None:
    assert set(NEW_LESSONS) <= set(LESSONS)
    for lesson_id in NEW_LESSONS:
        lesson = LESSONS[lesson_id]
        assert lesson.id == lesson_id and lesson.module_id == "m1_talking"
        assert lesson_id in BUILT_IN_RULES
        assert lesson.variant_ids() == []  # the same for everyone
        assert (REAL_CONTENT / "lessons" / f"{lesson_id}.json").exists()
    assert set(LESSONS) == BUILT_IN_RULES  # built in the rules <=> a lesson file exists


def test_lesson_titles_match_plan_rules() -> None:
    titles = {
        lesson.id: lesson.title for module in BUNDLE.plan_rules.modules for lesson in module.lessons
    }
    for lesson_id, lesson in LESSONS.items():
        assert lesson.title == titles[lesson_id]


@pytest.mark.parametrize("lesson_id", NEW_LESSONS)
def test_variant_free_lessons_use_only_the_default_key(lesson_id: str) -> None:
    lesson = LESSONS[lesson_id]
    data = lesson.model_dump(by_alias=True, mode="json", exclude_none=True)

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("VariantMap"):
                    assert value == {}, (path, key)
                if key in (
                    "byVariant",
                    "roundsByVariant",
                    "cueByVariant",
                    "answers",
                    "bullets",
                ) and (isinstance(value, dict)):
                    assert set(value) <= {"default"}, (path, key)
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")

    walk(data, lesson_id)


def test_each_lesson_has_fallback_scenarios_for_every_roleplay_round() -> None:
    for lesson_id, lesson in LESSONS.items():
        screen = next(s for s in lesson.screens if isinstance(s, RoleplayScreen))
        by_id = {s.id: s for s in lesson.fallback_scenarios}
        assert set(screen.fallback_scenarios) <= set(by_id), lesson_id
        longest = max(len(rounds) for rounds in screen.rounds_by_variant.values())
        if lesson_id in NEW_LESSONS:  # m1_l1 (increment 12) lists 2 for its 3 rounds
            assert len(screen.fallback_scenarios) >= longest, lesson_id
        for scenario_id in screen.fallback_scenarios:
            answers = by_id[scenario_id].answers
            assert len(answers) >= 2 and {a.verdict for a in answers} >= {"best"}, scenario_id


def test_learn_screens_of_the_old_lessons_are_within_word_limit() -> None:
    for lesson_id in NEW_LESSONS:
        lesson = LESSONS[lesson_id]
        learn = [s for s in lesson.screens if isinstance(s, LearnScreen)]
        assert 3 <= len(learn) <= 5, lesson_id
        for screen in learn:
            variants = list((screen.bullets or {"": []}).values())
            for bullets in variants:  # a learner sees one variant's bullets
                text = [screen.body or "", *bullets, screen.extra_for_both or ""]
                assert _words(" ".join(text)) <= 90, (lesson_id, screen.id)
            assert _words(screen.title) <= 14, (lesson_id, screen.id)
        # a small interaction every 2-3 screens: no run of 3+ learn screens without a mini-task
        gap = 0
        for screen in learn:
            gap = 0 if screen.mini_task is not None else gap + 1
            assert gap <= 2, (lesson_id, screen.id)


def _rendered_lessons() -> list[tuple[str, str, list[dict[str, object]]]]:
    """m1_l1 as a learner sees it, for every recipient key and variant."""
    provider = JsonContentProvider.from_directory(REAL_CONTENT)
    return [
        (
            key,
            variant,
            render_lesson(
                provider.render_lesson("m1_l1", key, variant, BLANKS), variant, True
            ).screens,
        )
        for key in RECIPIENT_KEYS
        for variant in VARIANTS
    ]


def _shown_text(screen: dict[str, object]) -> list[str]:
    hidden = {"id", "type", "part", "image"}
    return _strings({k: v for k, v in screen.items() if k not in hidden})


def test_m1_l1_has_the_24_screens_of_the_new_schema() -> None:
    lesson = LESSONS["m1_l1"]
    assert len(lesson.screens) == 24 and lesson.variant_ids() == VARIANTS
    assert [s.type for s in lesson.screens].count("quiz") == 6
    assert lesson.screens[0].type == "intro" and lesson.screens[1].type == "setup"
    assert not any(s.type in ("learn", "setup_question") for s in lesson.screens)
    assert sum(s.sec or 0 for s in lesson.screens) == 543  # about 9 minutes


def test_m1_l1_content_screens_are_within_word_limits() -> None:
    for key, variant, screens in _rendered_lessons():
        for screen in (s for s in screens if s["type"] == "content"):
            body = " ".join(_strings(screen.get("body")))
            assert _words(body) <= 60, (key, variant, screen["id"])
            assert _words(" ".join(_shown_text(screen))) <= 90, (key, variant, screen["id"])


def test_m1_l1_renders_for_every_recipient_and_variant_without_leftovers() -> None:
    for key, variant, screens in _rendered_lessons():
        text = " ".join(t for screen in screens for t in _shown_text(screen))
        assert not re.search(r"\{\w+\}", text), (key, variant)
        # singular "they" never meets a verb written for he or she
        assert not re.search(r"\b[Tt]hey (asks|enjoys|isn't|is|has|was|doesn't|wants)\b", text)
        assert not re.search(r"\b[Tt]hey's\b", text), (key, variant)


def test_m1_l1_has_no_gendered_or_family_specific_hard_coded_words() -> None:
    text = " ".join(_lesson_text(LESSONS["m1_l1"]))
    banned = r"\b(she|he|her|hers|his|him|himself|herself|daughter|son|mother|father|Mom|Dad)\b"
    assert not re.search(banned, text), re.findall(banned, text)


def test_m1_l1_verdicts_use_the_shared_vocabulary() -> None:
    lesson = LESSONS["m1_l1"]
    scenario = next(s for s in lesson.screens if isinstance(s, ScenarioScreen))
    verdicts = {o.verdict for options in scenario.options_by_variant.values() for o in options}
    verdicts |= {a.verdict for f in lesson.fallback_scenarios for a in f.answers}
    assert verdicts == {"best", "okay", "try_again"}


def test_lesson_minutes_match_plan_rules() -> None:
    minutes = {
        lesson.id: lesson.minutes
        for module in BUNDLE.plan_rules.modules
        for lesson in module.lessons
        if lesson.built
    }
    assert minutes == {lesson_id: lesson.minutes for lesson_id, lesson in LESSONS.items()}


@pytest.mark.parametrize("lesson_id", NEW_LESSONS)
def test_every_answer_and_response_has_warm_feedback(lesson_id: str) -> None:
    lesson = LESSONS[lesson_id]
    for screen in lesson.screens:
        if hasattr(screen, "answers"):
            for answers in screen.answers.values():
                assert all(a.feedback.strip() for a in answers)
                assert not any(
                    re.match(r"\s*(wrong|incorrect|no\b)", a.feedback, re.I) for a in answers
                )
        if isinstance(screen, LearnScreen) and screen.mini_task:
            assert all(
                (o.response or "").strip()
                for o in screen.mini_task.options
                if o.correct is not None
            )
            assert not any(
                re.match(r"\s*(wrong|incorrect)", o.response or "", re.I)
                for o in screen.mini_task.options
            )


def test_lesson_text_has_no_banned_phrases() -> None:
    for lesson_id, lesson in LESSONS.items():
        for text in _lesson_text(lesson):
            for pattern in BANNED:
                assert not re.search(pattern, text, re.I), (lesson_id, pattern, text)


@pytest.mark.parametrize("lesson_id", NEW_LESSONS)
def test_new_lessons_use_recipient_not_pronoun_and_have_an_all_done_line(lesson_id: str) -> None:
    text = " ".join(_lesson_text(LESSONS[lesson_id]))
    assert not re.search(r"\{(pronoun|Pronoun|was|is|has|lives)\}", text)
    wrap = next(s for s in LESSONS[lesson_id].screens if s.type == "wrap")
    assert wrap.all_done_line


def test_roleplay_lines_of_new_lessons_are_short_and_neutral() -> None:
    for lesson_id in NEW_LESSONS:
        lesson = LESSONS[lesson_id]
        screen = next(s for s in lesson.screens if isinstance(s, RoleplayScreen))
        for rounds in screen.rounds_by_variant.values():
            assert len(rounds) == 3
            for r in rounds:
                assert _words(r.line) <= 15
                assert not re.search(r"[A-Z]{4,}|!{2,}", r.line)


def test_lesson_5_has_a_phrases_review_screen_with_an_empty_state_text() -> None:
    screens = [s for s in LESSONS["m1_l5"].screens if isinstance(s, PhrasesReviewScreen)]
    assert len(screens) == 1
    assert screens[0].empty_text.strip() and screens[0].intro.strip()


def test_lesson_5_has_what_you_can_handle_now_screen() -> None:
    learn = [s for s in LESSONS["m1_l5"].screens if isinstance(s, LearnScreen)]
    screen = next(s for s in learn if s.title == "What you can handle now")
    items = (screen.bullets or {})["default"]
    assert len(items) == 4  # one line for each of the four lessons before it


def _round_keys(lesson: LessonFile) -> set[tuple[str, str]]:
    """(line, mood) of every round of a lesson: the role-play and the day-2 practice round."""
    blocks = [next(s for s in lesson.screens if isinstance(s, RoleplayScreen)).rounds_by_variant]
    blocks.append(lesson.day2.practice_round.rounds_by_variant)
    return {
        (r.line, r.mood) for rounds_by in blocks for rounds in rounds_by.values() for r in rounds
    }


def test_lesson_5_mixed_practice_round_draws_rounds_from_earlier_lessons() -> None:
    review = LESSONS["m1_l5"]
    screen = next(s for s in review.screens if isinstance(s, RoleplayScreen))
    earlier = [LESSONS[f"m1_l{n}"] for n in range(1, 5)]
    earlier_rounds = [_round_keys(lesson) for lesson in earlier]
    mixed = [(r.line, r.mood) for r in screen.rounds_by_variant["default"]]
    assert len(mixed) == 3
    for key in mixed:
        assert any(key in rounds for rounds in earlier_rounds), key
    # more than one lesson is drawn from
    assert sum(any(key in rounds for key in mixed) for rounds in earlier_rounds) >= 2


def test_lesson_5_fallbacks_are_the_earlier_lessons_fallbacks_for_the_same_lines() -> None:
    review = LESSONS["m1_l5"]
    screen = next(s for s in review.screens if isinstance(s, RoleplayScreen))
    earlier = {
        (f.line, tuple(a.text for a in f.answers))
        for n in range(1, 5)
        for f in LESSONS[f"m1_l{n}"].fallback_scenarios
    }
    by_id = {f.id: f for f in review.fallback_scenarios}
    rounds = screen.rounds_by_variant["default"]
    assert len(screen.fallback_scenarios) == len(rounds)
    for scenario_id, round_ in zip(screen.fallback_scenarios, rounds, strict=True):
        scenario = by_id[scenario_id]
        assert scenario.line == round_.line
        assert (scenario.line, tuple(a.text for a in scenario.answers)) in earlier
