"""`POST /api/checkins`: the answer to the if-then plan of an earlier day."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.lessons.access import valid_variant
from app.application.ports import Clock, ContentProvider, IdGenerator, UnitOfWork
from app.domain.lessons.plans import IfThenPlan
from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS
from app.domain.lessons.variants import pick
from app.domain.session.entities import Session
from app.domain.today.checkins import (
    FOLLOW_UPS_KEY,
    OBSERVATION_TEXT_MAX,
    OUTCOMES,
    Checkin,
    CheckinAlreadyAnswered,
    CheckinNotDue,
    CheckinPlanNotFound,
    InvalidCheckinAnswer,
    Observation,
    ObservationSource,
    Outcome,
    checkin_due,
)


@dataclass(frozen=True)
class DoctorNoteInput:
    """The learner's choice on the doctor note: keep it for the visit sheet, with optional
    words of their own (else the lesson's doctor-note text is used)."""

    add_to_visit_sheet: bool
    text: str | None = None


@dataclass(frozen=True)
class PlanQuote:
    cue: str
    response: str
    reset: str | None


@dataclass(frozen=True)
class FollowUp:
    title: str
    text: str


@dataclass(frozen=True)
class CheckinResult:
    plan_id: str
    came_up: str
    outcome: Outcome | None
    response_text: str | None
    follow_ups: list[FollowUp]
    plan: PlanQuote
    observation_added: bool
    task_done: bool


def checkin_block(
    content: ContentProvider, session: Session, lesson_id: str, variant: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The rendered `day2` of the lesson and its check-in for the variant (Today reuses this)."""
    data = content.render_lesson(
        lesson_id,
        session.recipient_key or "",
        valid_variant(content, lesson_id, variant),
        runtime_values=dict.fromkeys(RUNTIME_PLACEHOLDERS, ""),
        display_name=session.display_name,
    )
    day2: dict[str, Any] = data["day2"]
    check_in: dict[str, Any] = pick(
        day2["checkIn"]["byVariant"], variant, day2["checkIn"]["checkInVariantMap"]
    )
    return day2, check_in


def plan_quote(plan: IfThenPlan) -> PlanQuote:
    """The user's own words, quoted back on the check-in."""
    return PlanQuote(plan.cue, plan.response, plan.reset)


class SubmitCheckin:
    """Order of checks: unknown plan (404), already answered (409), not due yet (409), then
    the answer against the lesson's options (422). `helped` marks the task done; the doctor
    note (or `noted`) stores an observation."""

    def __init__(
        self, uow: UnitOfWork, content: ContentProvider, ids: IdGenerator, clock: Clock
    ) -> None:
        self._uow = uow
        self._content = content
        self._ids = ids
        self._clock = clock

    async def execute(
        self,
        session: Session,
        plan_id: str,
        came_up: str,
        outcome: str | None,
        doctor_note: DoctorNoteInput | None = None,
    ) -> CheckinResult:
        now = session.app_now(self._clock.now())
        async with self._uow:
            plan = await self._uow.if_then_plans.get(session.id, plan_id)
            if plan is None:
                raise CheckinPlanNotFound(plan_id)
            if await self._uow.checkins.get(session.id, plan_id) is not None:
                raise CheckinAlreadyAnswered(plan_id)
            if not checkin_due(plan.created_at, now, session.timezone, has_checkin=False):
                raise CheckinNotDue(plan_id)
            progress = await self._uow.lesson_progress.get(session.id, plan_id)
            day2, check_in = checkin_block(
                self._content, session, plan_id, progress.variant if progress else None
            )
            chosen, response_text, follow_ups = self._answer(day2, check_in, came_up, outcome)
            final_outcome: Outcome | None = chosen
            task_done = final_outcome == "helped"
            await self._uow.checkins.add(Checkin(session.id, plan_id, came_up, final_outcome, now))
            props: dict[str, object] = {"planId": plan_id, "cameUp": came_up}
            if final_outcome is not None:
                props["outcome"] = final_outcome
            await self._uow.events.record(session.id, "checkin_answer", props, now)
            if task_done:
                await self._uow.tasks.mark_done(session.id, plan_id, now)
            observation = self._observation(session, plan_id, came_up, doctor_note, day2, now)
            if observation is not None:
                await self._uow.observations.add(observation)
            await self._uow.commit()
        return CheckinResult(
            plan_id,
            came_up,
            final_outcome,
            response_text,
            follow_ups,
            plan_quote(plan),
            observation is not None,
            task_done,
        )

    @staticmethod
    def _answer(
        day2: dict[str, Any], check_in: dict[str, Any], came_up: str, outcome: str | None
    ) -> tuple[Outcome | None, str | None, list[FollowUp]]:
        options = {o["id"]: o for o in check_in["options"]}
        if came_up not in options:
            raise InvalidCheckinAnswer("came_up", sorted(options))
        option = options[came_up]
        follow = check_in.get("followUp")
        if follow is None or follow["ifAnswer"] != came_up:
            return None, option.get("response"), []
        follow_options = {o["id"]: o for o in follow["options"]}
        if outcome is None or outcome not in follow_options or outcome not in OUTCOMES:
            raise InvalidCheckinAnswer("outcome", sorted(follow_options))
        picked = follow_options[outcome]
        wants_follow_ups = picked.get("next") == FOLLOW_UPS_KEY
        follow_ups = (
            [FollowUp(f["title"], f["text"]) for f in day2[FOLLOW_UPS_KEY]]
            if wants_follow_ups
            else []
        )
        chosen: Outcome = next(o for o in OUTCOMES if o == outcome)
        return chosen, picked.get("response"), follow_ups

    def _observation(
        self,
        session: Session,
        plan_id: str,
        came_up: str,
        note: DoctorNoteInput | None,
        day2: dict[str, Any],
        now: datetime,
    ) -> Observation | None:
        noted = came_up == "noted"
        if note is None and not noted:
            return None
        source: ObservationSource = "doctor_note" if note is not None else "checkin_noted"
        words = (note.text or "").strip() if note is not None else ""
        text = (words or day2["doctorNote"]["text"])[:OBSERVATION_TEXT_MAX]
        keep = noted or (note is not None and note.add_to_visit_sheet)
        return Observation(self._ids.new_id(), session.id, plan_id, source, text, keep, now)
