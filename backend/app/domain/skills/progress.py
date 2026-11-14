"""Skills progress: pure aggregation of finished role-play runs and scenario picks per skill."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.domain.lessons.progress import ScenarioAnswer
from app.domain.roleplay.run import RunRecord

BEST_VERDICT = "best"
MAX_SCORE = 3


@dataclass(frozen=True)
class RoleplayProgress:
    """`first_score` is the first turn of the first finished run (the first try), `latest_score`
    the last turn of the latest finished run. Scores only, never any text."""

    runs: int
    first_score: int | None
    latest_score: int | None
    max_score: int = MAX_SCORE


@dataclass(frozen=True)
class ScenarioProgress:
    practised: int  # distinct scenario screens answered
    best: int  # of those, the screens where the best answer was picked at least once


@dataclass(frozen=True)
class SkillProgress:
    skill_id: str
    roleplay: RoleplayProgress | None
    scenarios: ScenarioProgress | None


def skill_progress(
    runs: Sequence[RunRecord],
    answers: Sequence[ScenarioAnswer],
    skill_of_lesson: Callable[[str], str | None],
    skill_order: Sequence[str],
) -> list[SkillProgress]:
    """One entry per practised skill, in `skill_order`. `runs` are finished, oldest first;
    `answers` are oldest first; lessons with no skill are ignored."""
    runs_by_skill: dict[str, list[RunRecord]] = {}
    for record in runs:
        skill = skill_of_lesson(record.lesson_id)
        if skill is not None and record.run.turn_scores:
            runs_by_skill.setdefault(skill, []).append(record)
    screens_by_skill: dict[str, dict[tuple[str, str], bool]] = {}
    for answer in answers:
        skill = skill_of_lesson(answer.lesson_id)
        if skill is None:
            continue
        screens = screens_by_skill.setdefault(skill, {})
        key = (answer.lesson_id, answer.screen_id)
        screens[key] = screens.get(key, False) or answer.verdict == BEST_VERDICT
    result: list[SkillProgress] = []
    for skill in skill_order:
        skill_runs = runs_by_skill.get(skill)
        skill_screens = screens_by_skill.get(skill)
        if not skill_runs and not skill_screens:
            continue
        result.append(
            SkillProgress(
                skill,
                None
                if not skill_runs
                else RoleplayProgress(
                    len(skill_runs),
                    skill_runs[0].run.turn_scores[0],
                    skill_runs[-1].run.turn_scores[-1],
                ),
                None
                if not skill_screens
                else ScenarioProgress(
                    len(skill_screens), sum(1 for hit in skill_screens.values() if hit)
                ),
            )
        )
    return result
