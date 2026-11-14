"""Plan use cases: complete the quiz (build and store the plan), preview, gift sheet."""

from app.application.plan.dto import CompleteResult, GiftPhrase, GiftSheet, PlanPreviewView
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.plan.builder import PlanBuilder
from app.domain.plan.entities import StoredPlan
from app.domain.plan.errors import NoPlan
from app.domain.quiz.definition import CONFIDENCE_QUESTION_ID, RECIPIENT_QUESTION_ID
from app.domain.quiz.entities import QuizState
from app.domain.quiz.plan_inputs import plan_inputs
from app.domain.session.entities import Session
from app.domain.shared.labels import render_text


class CompleteQuiz:
    """Validates the quiz, stores `confidence.day0` and (re)builds the plan snapshot.

    Calling it again after answers were edited rebuilds the plan. Once the subscription has
    started the quiz is locked, so `QuizState.complete` raises and the stored plan is untouched.
    """

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock

    async def execute(self, session: Session) -> CompleteResult:
        definition = self._content.quiz_definition()
        rules = self._content.plan_rules()
        now = self._clock.now()
        async with self._uow:
            state = await self._uow.quiz.get(session.id) or QuizState(session.id)
            state.complete(definition, now)
            inputs = plan_inputs(definition, state.answers)
            built = PlanBuilder.build(
                tags=state.tags,
                branch=state.branch or "",
                labels=self._content.recipient_labels(state.answers[RECIPIENT_QUESTION_ID]),
                q5_order=inputs.q5_order,
                rules=rules,
                heard=inputs.heard,
            )
            stored = StoredPlan(
                session_id=session.id,
                plan=built,
                rules_version=rules.version,
                content_version=self._content.content_version,
                lessons_per_week=built.pace.lessons_per_week,
                gift_phrase_ids=built.gift_phrase_ids,
                built_at=now,
            )
            await self._uow.plans.save(stored)
            await self._uow.confidence.save_day0(session.id, state.answers[CONFIDENCE_QUESTION_ID])
            await self._uow.quiz.save(state)
            await self._uow.commit()
        return CompleteResult(now, stored.rules_version, stored.content_version)


class GetPlanPreview:
    """Reads the stored snapshot only: content edits never reshuffle an existing plan."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, session: Session) -> PlanPreviewView:
        async with self._uow:
            stored = await self._uow.plans.get(session.id)
        if stored is None:
            raise NoPlan()
        return PlanPreviewView(
            stored.plan, stored.rules_version, stored.content_version, stored.built_at
        )


class GetGiftSheet:
    """The free phrase sheet: the plan's stored phrase ids, rendered with the recipient labels."""

    def __init__(self, uow: UnitOfWork, content: ContentProvider) -> None:
        self._uow = uow
        self._content = content

    async def execute(self, session: Session) -> GiftSheet:
        async with self._uow:
            stored = await self._uow.plans.get(session.id)
        if stored is None or session.recipient_key is None:
            raise NoPlan()
        labels = self._content.recipient_labels(session.recipient_key)
        bank = {p.id: p for p in self._content.phrases()}
        sheet = self._content.phrase_sheet()
        return GiftSheet(
            title=render_text(sheet.title, labels),
            intro=render_text(sheet.intro, labels),
            phrases=[
                GiftPhrase(p.id, render_text(p.text, labels), render_text(p.when, labels))
                for p in (bank[i] for i in stored.gift_phrase_ids if i in bank)
            ],
            footer=render_text(sheet.footer, labels),
        )
