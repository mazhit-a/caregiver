"""`SubmitRoleplayTurn`: one caregiver reply, in the fixed order validate -> safety -> rate limit
-> coach (under one deadline) -> strict validation -> rules -> store the score only."""

import asyncio
import logging
from collections.abc import Sequence
from uuid import UUID

from app.application.ports import (
    Clock,
    Coach,
    CoachUnavailable,
    ContentProvider,
    RateLimiter,
    UnitOfWork,
)
from app.application.roleplay.dto import (
    CoachInput,
    PreviousTurn,
    RoundView,
    SafetyKindView,
    TurnMode,
    TurnView,
)
from app.application.roleplay.lesson_source import Json, fallback_scenarios, render, rounds_for
from app.application.roleplay.limiter import LlmConcurrencyLimiter
from app.application.roleplay.runs import load_run, save_run
from app.domain.roleplay.errors import (
    InvalidCoachOutput,
    RateLimited,
    RoundMismatch,
    RunFinished,
    TooManyPreviousTurns,
)
from app.domain.roleplay.run import RunMode, RunRecord, validate_reply
from app.domain.roleplay.verdict import CoachOutcome, OutcomeKind, apply_rules, validate_verdict
from app.domain.safety.check import SafetyCheck, SafetyKind
from app.domain.session.entities import Session
from app.domain.shared.labels import RecipientLabels

logger = logging.getLogger(__name__)

MAX_PREVIOUS_TURNS = 3
EMERGENCY_RESOURCE_ID = "emergency_911"


class SubmitRoleplayTurn:
    """`deadline_seconds` is the single wall-clock budget of the model part of a turn (limiter
    acquire, coach call, rules); wire `Settings.llm_timeout_seconds`. `llm_limiter` is one
    process-wide instance. Logs ids, round and mode only, never reply or model text."""

    def __init__(
        self,
        uow: UnitOfWork,
        content: ContentProvider,
        coach: Coach,
        clock: Clock,
        rate_limiter: RateLimiter,
        llm_limiter: LlmConcurrencyLimiter,
        deadline_seconds: float,
    ) -> None:
        self._uow = uow
        self._content = content
        self._coach = coach
        self._clock = clock
        self._rate_limiter = rate_limiter
        self._llm_limiter = llm_limiter
        self._deadline = deadline_seconds

    async def execute(
        self,
        session: Session,
        run_id: UUID,
        round_number: int,
        reply: str,
        previous_turns: Sequence[PreviousTurn] = (),
    ) -> TurnView:
        reply = validate_reply(reply)
        if len(previous_turns) > MAX_PREVIOUS_TURNS:
            raise TooManyPreviousTurns(MAX_PREVIOUS_TURNS)
        record = await load_run(self._uow, session, run_id)
        if record.is_finished:
            raise RunFinished()
        lesson = render(self._content, session, record.lesson_id, record.variant)
        rounds = rounds_for(lesson, record.context, record.variant)
        self._check_round(record, round_number, len(rounds))

        safety = SafetyCheck.classify(reply, self._content.safety_terms())
        if safety is SafetyKind.CRISIS:
            return await self._stop(session, record, round_number)
        if safety is SafetyKind.EMERGENCY:
            return self._emergency(record, round_number)
        if not await self._rate_limiter.allow(str(session.id), self._clock.now()):
            raise RateLimited()
        if record.run.mode is RunMode.FALLBACK:
            return self._fallback(record, lesson, round_number)

        labels = self._content.lesson_recipient_labels(
            session.recipient_key or "", session.display_name
        )
        async with self._uow:
            profile = await self._uow.profiles.get(session.id)
        coach_input = _coach_input(
            labels,
            record,
            rounds[round_number - 1],
            round_number,
            reply,
            previous_turns,
            profile.calms if profile is not None else (),
        )
        outcome = await self._ask(coach_input, labels)
        if outcome is None:
            record.run.switch_to_fallback()
            await save_run(self._uow, record)
            logger.info("roleplay turn run=%s round=%s mode=fallback", record.id, round_number)
            return self._fallback(record, lesson, round_number)
        if outcome.kind is OutcomeKind.CRISIS:
            return await self._stop(session, record, round_number)
        record.run.record_turn(outcome.score, outcome.goals)
        await save_run(self._uow, record)
        logger.info("roleplay turn run=%s round=%s mode=ai", record.id, round_number)
        return TurnView(TurnMode.AI, round_number, record.run.rounds_total, coach=outcome)

    def _check_round(self, record: RunRecord, round_number: int, total: int) -> None:
        """AI runs take rounds in order; a fallback run only needs a round that exists."""
        expected = len(record.run.turn_scores) + 1
        in_range = 1 <= round_number <= total
        if (record.run.mode is RunMode.AI and round_number != expected) or not in_range:
            raise RoundMismatch(expected, round_number)

    async def _ask(self, coach_input: CoachInput, labels: RecipientLabels) -> CoachOutcome | None:
        """None means fallback: deadline, limiter full, coach failure or invalid output."""
        try:
            return await asyncio.wait_for(self._guarded(coach_input, labels), self._deadline)
        except (TimeoutError, CoachUnavailable, InvalidCoachOutput):
            return None

    async def _guarded(self, coach_input: CoachInput, labels: RecipientLabels) -> CoachOutcome:
        if not self._llm_limiter.try_acquire():
            raise CoachUnavailable("The coach is busy.")
        try:
            verdict = validate_verdict(await self._coach.turn(coach_input))
            return apply_rules(verdict, self._content.coach_tips(), labels, coach_input.label)
        finally:
            self._llm_limiter.release()

    async def _stop(self, session: Session, record: RunRecord, round_number: int) -> TurnView:
        """Crisis (local or from the model): the run ends and the crisis resources are shown."""
        record.finished_at = session.app_now(self._clock.now())
        await save_run(self._uow, record)
        logger.info(
            "roleplay turn run=%s round=%s mode=safety kind=crisis", record.id, round_number
        )
        return TurnView(
            TurnMode.SAFETY,
            round_number,
            record.run.rounds_total,
            kind=SafetyKindView.CRISIS,
            resources=tuple(self._content.crisis_resources()),
        )

    def _emergency(self, record: RunRecord, round_number: int) -> TurnView:
        resources = tuple(self._content.crisis_resources())
        text = next((r.description for r in resources if r.id == EMERGENCY_RESOURCE_ID), None)
        logger.info(
            "roleplay turn run=%s round=%s mode=safety kind=emergency", record.id, round_number
        )
        return TurnView(
            TurnMode.SAFETY,
            round_number,
            record.run.rounds_total,
            kind=SafetyKindView.EMERGENCY,
            resources=resources,
            emergency_text=text,
        )

    def _fallback(self, record: RunRecord, lesson: Json, round_number: int) -> TurnView:
        return TurnView(
            TurnMode.FALLBACK,
            round_number,
            record.run.rounds_total,
            fallback_scenarios=fallback_scenarios(lesson),
            run_mode=RunMode.FALLBACK,
        )


def _coach_input(
    labels: RecipientLabels,
    record: RunRecord,
    current: RoundView,
    round_number: int,
    reply: str,
    previous_turns: Sequence[PreviousTurn],
    calms: tuple[str, ...],
) -> CoachInput:
    """Only the prompt-contract fields; `calms` comes from the profile (empty without one)."""
    return CoachInput(
        label=labels.recipient,
        variant=record.variant,
        round=round_number,
        rounds_total=record.run.rounds_total,
        stage=current.stage,
        parent_line=current.line,
        parent_mood=current.mood,
        calms=calms,
        previous_turns=tuple(previous_turns),
        caregiver_reply=reply,
    )
