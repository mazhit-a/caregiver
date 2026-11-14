"""One test per server-side event emitter (increment 38), through the fake unit of work."""

from datetime import timedelta

from app.application.billing.events import BillingEvent
from app.application.billing.stripe_events import HandleStripeEvent
from app.application.checkins.use_cases import SubmitCheckin
from app.application.demo.renewals import RollDemoRenewals
from app.application.demo.use_cases import AdvanceDemoDay, JumpToRenewal
from app.application.lessons.complete import CompleteLesson
from app.application.roleplay.dto import TurnPhrase
from app.domain.billing.entities import Subscription
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.billing.test_stripe_events import END, _consented
from tests.application.billing.test_stripe_events import content as stripe_content  # noqa: F401
from tests.application.care_card.test_care_card_use_cases import publisher, save_phrase, setup
from tests.application.checkins.test_submit_checkin import with_if_then_plan
from tests.application.demo.test_roll_demo_renewals import _setup as demo_setup
from tests.application.demo.test_roll_demo_renewals import content as demo_content  # noqa: F401
from tests.application.lessons.test_get_lesson import content  # noqa: F401
from tests.application.lessons.test_plan_wrap_complete import prepared
from tests.application.roleplay.helpers import make_rig, verdict
from tests.fakes.clock import FixedClock
from tests.fakes.events import InMemoryEventLog
from tests.fakes.roleplay import FakeCoach
from tests.fakes.sessions import FakeIdGenerator
from tests.fakes.unit_of_work import FakeUnitOfWork


def only(log: InMemoryEventLog, name: str) -> list[dict[str, object]]:
    return [dict(e.props) for e in log.events if e.name == name]


async def test_complete_lesson_emits_lesson_complete(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, _ = await prepared(uow, clock, content)
    use_case = CompleteLesson(uow, content, clock)
    await use_case.execute(session, "m1_l1")
    await use_case.execute(session, "m1_l1")  # a repeat does not count twice
    assert only(uow.events, "lesson_complete") == [{"lessonId": "m1_l1"}]
    assert uow.events.events[0].app_at == session.app_now(clock.now())


async def test_finish_roleplay_emits_roleplay_finish_without_text(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    rig = await make_rig(uow, clock, content)
    view = await rig.start()
    reply = "ZEBRA-REPLY you sound worried, I'm here"
    await rig.turn_use_case(
        FakeCoach(verdict(True, True, False, better_phrase="ZEBRA-BETTER"))
    ).execute(rig.session, view.run_id, 1, reply)
    phrases = [TurnPhrase(reply, "ZEBRA-BETTER")]
    await rig.finish_use_case().execute(rig.session, view.run_id, phrases)
    await rig.finish_use_case().execute(rig.session, view.run_id, phrases)  # idempotent
    (props,) = only(uow.events, "roleplay_finish")
    assert props == {
        "lessonId": "m1_l1",
        "context": "lesson",
        "mode": "ai",
        "turns": 1,
        "firstScore": 2,
        "lastScore": 2,
    }
    assert "ZEBRA" not in repr(uow.events.events)


async def test_submit_checkin_emits_checkin_answer(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    await SubmitCheckin(uow, content, FakeIdGenerator(), clock).execute(
        session, "m1_l1", "yes", "helped"
    )
    assert only(uow.events, "checkin_answer") == [
        {"planId": "m1_l1", "cameUp": "yes", "outcome": "helped"}
    ]


async def test_publish_card_emits_card_published(uow: FakeUnitOfWork, clock: FixedClock) -> None:
    s = await setup(uow, clock, recipient_key="mom")
    a = await save_phrase(uow, s, clock, "A phrase that is free text")
    await publisher(uow, clock).execute(s, [a])
    assert only(uow.events, "card_published") == [{"phrases": 1}]
    assert "free text" not in repr(uow.events.events)


async def test_next_day_emits_demo_next_day_and_jump_emits_its_event(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    demo_content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await demo_setup(uow, clock)
    await AdvanceDemoDay(uow, clock).execute(session)
    assert only(uow.events, "demo_next_day") == [{}]
    assert uow.events.events[0].app_at == clock.now() + timedelta(days=1)
    await JumpToRenewal(uow, clock).execute(session)
    assert only(uow.events, "demo_jump_to_renewal") == [{}]


async def test_demo_renewal_emits_renewed_event(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    demo_content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await demo_setup(uow, clock)
    await RollDemoRenewals(uow, demo_content).execute(session, clock.now() + timedelta(days=57))
    assert only(uow.events, "renewed") == [
        {"source": "demo", "renewalCount": 1},
        {"source": "demo", "renewalCount": 2},
    ]
    assert uow.events.events[0].app_at == clock.now() + timedelta(days=28)


async def test_stripe_invoice_paid_emits_renewed_once_per_paid_period(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    stripe_content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await _consented(uow, clock, stripe_content)
    handler = HandleStripeEvent(uow, stripe_content, clock)
    await handler.execute(
        BillingEvent(
            "e1",
            "checkout.session.completed",
            session_id=session.id,
            customer_id="cus_1",
            subscription_id="sub_1",
            plan_id="four_week",
            paid=True,
        )
    )
    assert only(uow.events, "renewed") == []  # the start is not a renewal
    paid = BillingEvent("e2", "invoice.paid", customer_id="cus_1", period_end=END)
    await handler.execute(paid)
    again = BillingEvent("e3", "invoice.paid", customer_id="cus_1", period_end=END)
    await handler.execute(again)  # same period: no second renewal
    assert only(uow.events, "renewed") == [{"source": "stripe", "renewalCount": 1}]
    sub: Subscription | None = await uow.subscriptions.get(session.id)
    assert sub is not None and sub.renewal_count == 1
