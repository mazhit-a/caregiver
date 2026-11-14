import asyncio
import json
import logging
import re
from dataclasses import asdict, fields, replace
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest

from app.application.roleplay.dto import CoachInput, PreviousTurn, TurnMode, TurnPhrase
from app.domain.lessons.errors import LessonLocked
from app.domain.profile.entities import Profile
from app.domain.roleplay.errors import (
    InvalidReply,
    RateLimited,
    RoundMismatch,
    RunFinished,
    RunNotFound,
    TooManyPreviousTurns,
    TurnsMismatch,
)
from app.domain.roleplay.run import RunContext, RunMode
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.lessons.test_get_lesson import content  # noqa: F401
from tests.application.roleplay.helpers import Rig, make_rig, verdict
from tests.fakes.clock import FixedClock
from tests.fakes.roleplay import FakeCoach, unavailable
from tests.fakes.unit_of_work import FakeUnitOfWork

REPLY = "You sound worried about tomorrow. I'm here and I'll handle it. Want some tea?"
REPO = Path(__file__).resolve().parents[4]
VARIANTS = JsonContentProvider.from_directory(REPO / "content").lesson_variants("m1_l1")


@pytest.fixture
async def rig(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> Rig:
    return await make_rig(uow, clock, content)


# ---------------------------------------------------------------- start


@pytest.mark.parametrize("variant", VARIANTS)
async def test_start_practice_round_uses_day2_practice_round_rounds_for_the_stored_variant(
    rig: Rig, variant: str
) -> None:
    view = await rig.start(RunContext.PRACTICE_ROUND, variant)
    lesson = rig.content.render_lesson(
        "m1_l1", "dad", variant, {"savedPhrase": "", "firstScore": "", "lastScore": ""}
    )
    block = lesson["day2"]["practiceRound"]
    expected = block["roundsByVariant"][block["roundsVariantMap"][variant]]
    assert [(r.stage, r.line, r.mood) for r in view.rounds] == [
        (r["stage"], r["line"], r["mood"]) for r in expected
    ]
    assert view.variant == variant and view.intro is None


async def test_start_lesson_context_uses_lesson_roleplay_rounds(rig: Rig) -> None:
    view = await rig.start(RunContext.LESSON, "phone")
    lesson = rig.content.render_lesson(
        "m1_l1", "dad", "phone", {"savedPhrase": "", "firstScore": "", "lastScore": ""}
    )
    screen = next(s for s in lesson["screens"] if s["type"] == "roleplay")
    assert [(r.stage, r.line, r.mood) for r in view.rounds] == [
        (r["stage"], r["line"], r["mood"]) for r in screen["roundsByVariant"]["phone"]
    ]
    assert view.intro == screen["intro"] and "{" not in view.intro


async def test_practice_round_run_stored_with_context_practice_round_and_finished_at_app_time(
    rig: Rig,
) -> None:
    view = await rig.start(RunContext.PRACTICE_ROUND, "phone")
    stored = rig.uow.roleplay_runs.rows[view.run_id]
    app_now = rig.clock.now() + timedelta(days=2)
    assert stored.context is RunContext.PRACTICE_ROUND and stored.started_at == app_now
    assert stored.finished_at is None
    await rig.turn_use_case(FakeCoach()).execute(rig.session, view.run_id, 1, REPLY)
    rig.clock.advance(timedelta(minutes=3))
    finished = await rig.finish_use_case().execute(
        rig.session, view.run_id, [TurnPhrase(REPLY, "x")]
    )
    assert finished.finished_at == app_now + timedelta(minutes=3)
    assert rig.uow.roleplay_runs.rows[view.run_id].finished_at == finished.finished_at


async def test_start_is_gated_by_lesson_access(rig: Rig) -> None:
    with pytest.raises(LessonLocked):
        await rig.start_use_case().execute(rig.session, "m1_l2", RunContext.LESSON)


# ---------------------------------------------------------------- safety


async def test_crisis_reply_never_calls_coach(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach()
    result = await rig.turn_use_case(coach).execute(
        rig.session, view.run_id, 1, "I want to die, I can't do this"
    )
    assert coach.calls == []
    assert result.mode is TurnMode.SAFETY and result.kind is not None
    assert result.kind.value == "crisis" and result.resources
    assert rig.uow.roleplay_runs.rows[view.run_id].finished_at is not None
    with pytest.raises(RunFinished):
        await rig.turn_use_case(coach).execute(rig.session, view.run_id, 1, REPLY)


async def test_emergency_reply_returns_911_text_and_skips_coach(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach()
    result = await rig.turn_use_case(coach).execute(
        rig.session, view.run_id, 1, "She fell in the bathroom"
    )
    assert coach.calls == []
    assert result.mode is TurnMode.SAFETY and result.kind is not None
    assert result.kind.value == "emergency"
    assert result.emergency_text == "If this is happening now, call 911."
    assert rig.uow.roleplay_runs.rows[view.run_id].finished_at is None  # paused, not stopped


async def test_excluded_phrase_does_not_trigger_the_emergency(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach()
    result = await rig.turn_use_case(coach).execute(
        rig.session, view.run_id, 1, "You sound worried, I was missing the bus. Tea?"
    )
    assert result.mode is TurnMode.AI and len(coach.calls) == 1


async def test_model_crisis_flag_stops_run_like_local_check(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach(verdict(False, False, False, flags=("crisis",)))
    result = await rig.turn_use_case(coach).execute(rig.session, view.run_id, 1, REPLY)
    assert result.mode is TurnMode.SAFETY and result.kind is not None
    assert result.kind.value == "crisis" and result.resources and result.coach is None
    stored = rig.uow.roleplay_runs.rows[view.run_id]
    assert stored.finished_at is not None and stored.run.turn_scores == []


# ---------------------------------------------------------------- coach input


async def test_coach_input_contains_no_quiz_answers_or_visit_sheet_data(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach()
    previous = [PreviousTurn("When are we going?", "Tomorrow at 2.", 1)]
    await rig.turn_use_case(coach).execute(rig.session, view.run_id, 1, REPLY, previous)
    (sent,) = coach.calls
    assert isinstance(sent, CoachInput)
    assert {f.name for f in fields(sent)} == {
        "label",
        "variant",
        "round",
        "rounds_total",
        "stage",
        "parent_line",
        "parent_mood",
        "calms",
        "previous_turns",
        "caregiver_reply",
    }
    assert sent.caregiver_reply == REPLY and sent.label == "Dad" and sent.variant == "phone"
    assert sent.round == 1 and sent.rounds_total == 3 and sent.calms == ()
    assert sent.previous_turns == tuple(previous)
    quiz = await rig.uow.quiz.get(rig.session.id)
    assert quiz is not None
    blob = repr(asdict(sent)).lower()
    for answer in quiz.answers.values():
        for item in answer if isinstance(answer, list) else [answer]:
            if isinstance(item, str) and len(item) > 3:
                assert item.lower() not in blob


# ---------------------------------------------------------------- fallback


FAILURES = {
    "timeout": unavailable(),
    "api_error": unavailable(),
    "refusal": unavailable(),
    "invalid_json": unavailable(),
}


@pytest.mark.parametrize("name", FAILURES)
async def test_timeout_error_refusal_and_invalid_json_each_return_fallback_scenarios(
    rig: Rig, name: str
) -> None:
    view = await rig.start()
    result = await rig.turn_use_case(FakeCoach(FAILURES[name])).execute(
        rig.session, view.run_id, 1, REPLY
    )
    assert result.mode is TurnMode.FALLBACK and result.coach is None
    assert [s["id"] for s in result.fallback_scenarios] == ["fb1", "fb2"]
    assert not re.search(r"\{\w+\}", json.dumps(result.fallback_scenarios))
    assert rig.uow.roleplay_runs.rows[view.run_id].run.mode is RunMode.FALLBACK


async def test_output_with_unknown_flag_returns_fallback(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach(verdict(True, True, True, flags=("surprise",)))
    result = await rig.turn_use_case(coach).execute(rig.session, view.run_id, 1, REPLY)
    assert result.mode is TurnMode.FALLBACK


async def test_run_stays_fallback_for_remaining_rounds(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach(unavailable())
    use_case = rig.turn_use_case(coach)
    await use_case.execute(rig.session, view.run_id, 1, REPLY)
    result = await use_case.execute(rig.session, view.run_id, 2, REPLY)  # coach is healthy now
    assert result.mode is TurnMode.FALLBACK and len(coach.calls) == 1


async def test_fifth_concurrent_call_returns_fallback_immediately(rig: Rig) -> None:
    runs = [await rig.start() for _ in range(5)]
    gate = asyncio.Event()
    coach = FakeCoach(gate=gate)
    use_case = rig.turn_use_case(coach, deadline=30)
    tasks = [
        asyncio.create_task(use_case.execute(rig.session, r.run_id, 1, REPLY)) for r in runs[:4]
    ]
    await coach.wait_for_calls(4)
    fifth = await use_case.execute(rig.session, runs[4].run_id, 1, REPLY)
    assert fifth.mode is TurnMode.FALLBACK and len(coach.calls) == 4
    gate.set()
    results = await asyncio.gather(*tasks)
    assert [r.mode for r in results] == [TurnMode.AI] * 4
    assert rig.llm_limiter.in_flight == 0


async def test_turn_over_deadline_returns_fallback_and_switches_run(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach(gate=asyncio.Event())  # never set: the coach hangs
    result = await rig.turn_use_case(coach, deadline=0.01).execute(
        rig.session, view.run_id, 1, REPLY
    )
    assert result.mode is TurnMode.FALLBACK
    assert rig.uow.roleplay_runs.rows[view.run_id].run.mode is RunMode.FALLBACK
    assert rig.llm_limiter.in_flight == 0


# ---------------------------------------------------------------- limits and validation


async def test_41st_turn_in_an_hour_raises_rate_limited(rig: Rig) -> None:
    view = await rig.start()
    use_case = rig.turn_use_case(FakeCoach(unavailable()), per_hour=40)
    for _ in range(40):
        await use_case.execute(rig.session, view.run_id, 1, REPLY)  # fallback after the first
    with pytest.raises(RateLimited):
        await use_case.execute(rig.session, view.run_id, 1, REPLY)
    rig.clock.advance(timedelta(hours=1, seconds=1))
    assert (await use_case.execute(rig.session, view.run_id, 1, REPLY)).mode is TurnMode.FALLBACK


async def test_reply_501_chars_rejected(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach()
    use_case = rig.turn_use_case(coach)
    with pytest.raises(InvalidReply):
        await use_case.execute(rig.session, view.run_id, 1, "x" * 501)
    with pytest.raises(InvalidReply):
        await use_case.execute(rig.session, view.run_id, 1, "   ")
    assert coach.calls == []


async def test_round_mismatch_rejected(rig: Rig) -> None:
    view = await rig.start()
    use_case = rig.turn_use_case(FakeCoach())
    with pytest.raises(RoundMismatch):
        await use_case.execute(rig.session, view.run_id, 2, REPLY)
    with pytest.raises(RoundMismatch):
        await use_case.execute(rig.session, view.run_id, 0, REPLY)


async def test_previous_turns_over_3_rejected(rig: Rig) -> None:
    view = await rig.start()
    turns = [PreviousTurn("p", "c", 1)] * 4
    with pytest.raises(TooManyPreviousTurns):
        await rig.turn_use_case(FakeCoach()).execute(rig.session, view.run_id, 1, REPLY, turns)


async def test_other_sessions_run_is_not_found(rig: Rig) -> None:
    view = await rig.start()
    other = replace(rig.session, id=UUID(int=99))
    with pytest.raises(RunNotFound):
        await rig.turn_use_case(FakeCoach()).execute(other, view.run_id, 1, REPLY)


# ---------------------------------------------------------------- finish and privacy


async def test_finish_summary_first_vs_last_and_best_phrase(rig: Rig) -> None:
    view = await rig.start()
    coach = FakeCoach(
        verdict(True, False, False, better_phrase="BETTER ONE"),
        verdict(True, True, False, better_phrase="BETTER TWO"),
        verdict(True, True, True, better_phrase="BETTER THREE"),
    )
    use_case = rig.turn_use_case(coach)
    replies = ["first reply", "second reply", "third reply that is perfect"]
    for number, reply in enumerate(replies, start=1):
        await use_case.execute(rig.session, view.run_id, number, reply)
    phrases = [
        TurnPhrase(r, f"BETTER {n}") for r, n in zip(replies, ("ONE", "TWO", "THREE"), strict=True)
    ]
    done = await rig.finish_use_case().execute(rig.session, view.run_id, phrases)
    assert done.scores == (1, 2, 3)
    assert done.summary.first_score == 1 and done.summary.last_score == 3
    assert done.summary.improved and done.summary.notice_turns == 3
    assert done.summary.reassure_turns == 2 and done.summary.offer_turns == 1
    assert done.first_vs_last == "First try: 1 of 3 · Last try: 3 of 3"
    assert done.best_phrase == "third reply that is perfect"
    with pytest.raises(TurnsMismatch):
        await rig.finish_use_case().execute(rig.session, view.run_id, phrases[:2])


async def test_finish_without_a_perfect_reply_uses_the_last_better_phrase(rig: Rig) -> None:
    view = await rig.start()
    await rig.turn_use_case(FakeCoach(verdict(True, False, False))).execute(
        rig.session, view.run_id, 1, "ok then"
    )
    done = await rig.finish_use_case().execute(
        rig.session, view.run_id, [TurnPhrase("ok then", "  Try this  ")]
    )
    assert done.best_phrase == "Try this"


async def test_finish_of_a_fallback_run_has_no_scores_or_phrase(rig: Rig) -> None:
    view = await rig.start()
    await rig.turn_use_case(FakeCoach(unavailable())).execute(rig.session, view.run_id, 1, REPLY)
    done = await rig.finish_use_case().execute(rig.session, view.run_id)
    assert done.mode is RunMode.FALLBACK and done.first_vs_last is None
    assert done.best_phrase is None and done.scores == ()


async def test_no_reply_text_in_persisted_run_rows_or_log_records(
    rig: Rig, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    view = await rig.start()
    secret_reply = "ZEBRA-REPLY you sound worried, I'm here, want tea?"
    model_texts = ("ZEBRA-TIP", "ZEBRA-BETTER", "ZEBRA-REACTION")
    coach = FakeCoach(
        verdict(
            True,
            True,
            True,
            tip=model_texts[0],
            better_phrase=model_texts[1],
            parent_reaction=model_texts[2],
        )
    )
    result = await rig.turn_use_case(coach).execute(rig.session, view.run_id, 1, secret_reply)
    assert result.coach is not None and result.coach.tip == "ZEBRA-TIP"  # returned, not stored
    await rig.finish_use_case().execute(
        rig.session, view.run_id, [TurnPhrase(secret_reply, "ZEBRA-BETTER")]
    )
    rows = repr([asdict(r) for r in rig.uow.roleplay_runs.rows.values()])
    logs = " ".join(r.getMessage() + repr(r.__dict__) for r in caplog.records)
    assert caplog.records
    for text in (secret_reply, "ZEBRA", *model_texts):
        assert text not in rows and text not in logs


async def test_roleplay_input_uses_profile_calms(rig: Rig) -> None:
    profile = Profile.create(
        rig.session.id,
        ["gardening"],
        ["quiet music", "a cup of tea"],
        ["loud rooms"],
        "",
        [],
        None,
        rig.clock.now(),
    )
    await rig.uow.profiles.save(profile)
    view = await rig.start()
    coach = FakeCoach()
    await rig.turn_use_case(coach).execute(rig.session, view.run_id, 1, REPLY)
    (sent,) = coach.calls
    assert sent.calms == ("quiet music", "a cup of tea")
    blob = repr(asdict(sent)).lower()
    assert "gardening" not in blob and "loud rooms" not in blob  # only `calms` is passed on
    quiz = await rig.uow.quiz.get(rig.session.id)
    assert quiz is not None
    for answer in quiz.answers.values():
        for item in answer if isinstance(answer, list) else [answer]:
            if isinstance(item, str) and len(item) > 3:
                assert item.lower() not in blob  # still no quiz answers in the coach input
