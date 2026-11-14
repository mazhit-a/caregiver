"""BuiltPlan <-> JSON snapshot stored in `plans.snapshot` (plain dicts, snake_case keys)."""

from dataclasses import asdict
from typing import Any

from app.domain.plan.entities import (
    BeforeAfterRule,
    BuiltPlan,
    Pace,
    PlanLesson,
    PlanModule,
    PlanQuickGuide,
    Readiness,
)


def plan_to_snapshot(plan: BuiltPlan) -> dict[str, Any]:
    return asdict(plan)


def plan_from_snapshot(data: dict[str, Any]) -> BuiltPlan:
    return BuiltPlan(
        rules_version=data["rules_version"],
        plan_intro=data["plan_intro"],
        what_we_heard=tuple(data["what_we_heard"]),
        before_after=BeforeAfterRule(**data["before_after"]),
        modules=tuple(
            PlanModule(
                id=m["id"],
                title=m["title"],
                reason=m["reason"],
                status=m["status"],
                in_first_30_days=m["in_first_30_days"],
                lessons=tuple(PlanLesson(**lesson) for lesson in m["lessons"]),
            )
            for m in data["modules"]
        ),
        first_30_days=tuple(data["first_30_days"]),
        first_lesson_id=data["first_lesson_id"],
        quick_guides=tuple(PlanQuickGuide(**g) for g in data["quick_guides"]),
        loader_lines=tuple(data["loader_lines"]),
        pace=Pace(**data["pace"]),
        readiness=Readiness(**data["readiness"]),
        gift_phrase_ids=tuple(data["gift_phrase_ids"]),
    )
