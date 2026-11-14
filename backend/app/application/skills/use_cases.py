"""`GET /api/skills`: practice progress per skill, confidence, counts and what comes next."""

from app.application.plan.use_cases import GetPlan
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.application.skills.dto import ConfidenceView, SkillCounts, SkillsView, SkillView
from app.domain.plan.errors import NoPlan
from app.domain.schedule.entities import LessonState
from app.domain.schedule.next_lesson import select_next_lesson
from app.domain.session.entities import Session
from app.domain.skills.progress import skill_progress


class GetSkills:
    """Reads stored scores, verdicts and counts (never any role-play text). The next lesson
    uses the same plan read and selection (`select_next_lesson`) as Today."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._get_plan = GetPlan(uow, content, clock)

    async def execute(self, session: Session) -> SkillsView:
        plan_view = await self._get_plan.execute(session)  # raises NoPlan, extends the schedule
        rules = self._content.plan_rules()
        skill_by_lesson = {lesson.id: m.skill for m in rules.modules for lesson in m.lessons}
        async with self._uow:
            stored = await self._uow.plans.get(session.id)
            runs = await self._uow.roleplay_runs.list_finished(session.id)
            answers = await self._uow.scenario_answers.list_for_session(session.id)
            day0 = await self._uow.confidence.get_day0(session.id)
            ratings = await self._uow.confidence.get_ratings(session.id)
            phrases = await self._uow.saved_phrases.count(session.id)
            tasks = await self._uow.tasks.list_for_session(session.id)
            checkins = await self._uow.checkins.list_for_session(session.id)
        if stored is None:
            raise NoPlan()
        progress = skill_progress(
            runs,
            answers,
            lambda lesson_id: skill_by_lesson.get(lesson_id) or None,
            list(rules.skills),
        )
        states = [
            LessonState(lesson.id, lesson.status, lesson.unlock_on)
            for module in plan_view.modules
            for lesson in module.lessons
        ]
        return SkillsView(
            skills=[
                SkillView(p.skill_id, rules.skills[p.skill_id], p.roleplay, p.scenarios)
                for p in progress
            ],
            confidence=ConfidenceView(day0, ratings.first, ratings.latest),
            counts=SkillCounts(
                scenarios_practised=len({(a.lesson_id, a.screen_id) for a in answers}),
                phrases_saved=phrases,
                tasks_tried=len(tasks),
                tasks_helped=sum(1 for c in checkins if c.outcome == "helped"),
            ),
            next=select_next_lesson(stored.plan.modules, states),
        )
