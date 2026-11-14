from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.visit_sheet.use_cases import GetVisitSheet, UpdateVisitSheet, VisitSheetInput
from app.domain.session.entities import Session
from app.domain.today.checkins import Observation
from app.domain.visit_sheet.entities import UnknownVisitQuestion, VisitQuestionItem
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.lessons.test_get_lesson import with_plan
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.lesson_content import make_content_dir


@pytest.fixture
def content(tmp_path: Path) -> JsonContentProvider:
    return JsonContentProvider.from_directory(make_content_dir(tmp_path / "content"))


async def make_session(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> Session:
    return await with_plan(uow, clock, content)


async def test_empty_sheet_has_bank_and_footer(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await make_session(uow, clock, content)
    view = await GetVisitSheet(uow, content).execute(session)
    assert view.questions == [] and view.doctor is None and view.family_notes == ""
    assert view.footer == content.visit_questions().footer
    assert [q.id for q in view.bank] == [q.id for q in content.visit_questions().questions]


async def test_put_stores_words_as_typed_and_keeps_order(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await make_session(uow, clock, content)
    items = (
        VisitQuestionItem(None, "  Mine first?  "),
        VisitQuestionItem("q_tests"),
        VisitQuestionItem("q_changes"),
    )
    data = VisitSheetInput(" Dr. Lee ", date(2026, 12, 1), "  She asked 6x.\n", items)
    view = await UpdateVisitSheet(uow, content, clock).execute(session, data)
    assert view.doctor == " Dr. Lee " and view.family_notes == "  She asked 6x.\n"
    assert [(q.id, q.custom) for q in view.questions] == [
        (None, True),
        ("q_tests", False),
        ("q_changes", False),
    ]
    assert view.questions[0].text == "  Mine first?  "
    assert uow.committed


async def test_unknown_id_is_rejected_and_nothing_saved(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await make_session(uow, clock, content)
    data = VisitSheetInput(None, None, "", (VisitQuestionItem("zzz"),))
    with pytest.raises(UnknownVisitQuestion):
        await UpdateVisitSheet(uow, content, clock).execute(session, data)
    assert uow.visit_sheets.rows == {}


async def test_only_flagged_observations_are_suggested(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await make_session(uow, clock, content)
    now = clock.now()
    for text, keep, later in (("kept", True, 0), ("skipped", False, 1), ("kept 2", True, 2)):
        await uow.observations.add(
            Observation(
                uuid4(),
                session.id,
                "m1_l1",
                "doctor_note",
                text,
                keep,
                now + timedelta(minutes=later),
            )
        )
    other = Observation(uuid4(), uuid4(), "m1_l1", "doctor_note", "other", True, now)
    await uow.observations.add(other)
    view = await GetVisitSheet(uow, content).execute(session)
    assert [n.text for n in view.suggested_notes] == ["kept", "kept 2"]
