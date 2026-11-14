"""Billing use cases: pricing, subscription start (the single entry), demo start, read, gate."""

from app.application.billing.dto import PricingPlanView, PricingView, StartRequest
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.application.schedule.use_cases import EnsureSchedule
from app.domain.billing.entities import STARTED_STATUSES, Subscription
from app.domain.billing.errors import AlreadySubscribed, ConsentRequired
from app.domain.plan.errors import NoPlan
from app.domain.schedule.entities import PlanLessonRef, UnlockRule
from app.domain.session.entities import Session


class GetPricing:
    def __init__(self, content: ContentProvider, clock: Clock) -> None:
        self._content = content
        self._clock = clock

    def execute(self, session: Session | None) -> PricingView:
        """Without a session there is no app clock, so `first_renewal_date` is None."""
        today = session.app_today(self._clock.now()) if session is not None else None
        pricing = self._content.pricing()
        return PricingView(
            currency=pricing.currency,
            default_plan_id=pricing.default_plan_id,
            plans=[
                PricingPlanView(
                    id=p.id,
                    label=p.label,
                    price_today=p.intro_price,
                    renewal_price=p.renew_price,
                    intro_period_text=p.intro_period_text,
                    renew_period_text=p.renew_period_text,
                    intro_days=p.intro_days,
                    renew_days=p.renew_days,
                    first_renewal_date=p.first_renewal_date(today) if today is not None else None,
                )
                for p in pricing.plans
            ],
        )


class GetSubscription:
    """The session's subscription; a session that never subscribed gets status `none`."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, session: Session) -> Subscription:
        async with self._uow:
            return await self._uow.subscriptions.get(session.id) or Subscription(session.id)


class StartSubscription:
    """Starts a subscription: demo, Stripe return-page reconcile and Stripe webhook all call this.

    Idempotent: a subscription that is already started (any status but `none`) is returned
    unchanged, with no history entry, no purge and no second schedule. Otherwise, in one
    transaction: the consent is stored first (own save, before the status change), the status
    changes through the entity with history at app time, Q3/Q5 raw answers are purged and the
    quiz is locked. The lesson schedule is created right after (it is idempotent too).
    """

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._ensure_schedule = EnsureSchedule(uow)

    async def execute(self, session: Session, request: StartRequest) -> Subscription:
        now = session.app_now(self._clock.now())
        today = session.app_today(self._clock.now())
        plan = self._content.pricing().plan(request.plan_id)
        definition = self._content.quiz_definition()
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
            if subscription.status in STARTED_STATUSES:
                return subscription
            stored = await self._uow.plans.get(session.id)
            if stored is None:
                raise NoPlan()
            if subscription.auto_renew_consent_at is None and not request.auto_renew_consent:
                raise ConsentRequired()
            subscription.record_consent(now)
            await self._uow.subscriptions.save(subscription)  # consent first, then the status
            if request.source == "demo":
                subscription.start_demo(now, plan.id, plan.intro_days)
            else:
                if request.period_end is None:
                    raise ValueError("A Stripe start needs the period end")
                subscription.start_stripe(
                    now,
                    plan.id,
                    request.period_end,
                    request.stripe_customer_id,
                    request.stripe_subscription_id,
                )
            await self._uow.subscriptions.save(subscription)
            for entry in subscription.pull_history():
                await self._uow.subscription_history.add(entry)
            quiz = await self._uow.quiz.get(session.id)
            if quiz is not None:
                quiz.purge_health_answers(definition, now)
                quiz.lock()
                await self._uow.quiz.save(quiz)
            await self._uow.commit()
        await self._ensure_schedule.execute(
            session.id,
            today,
            stored.lessons_per_week,
            [
                PlanLessonRef(lesson.id, lesson.built)
                for module in stored.plan.modules
                for lesson in module.lessons
            ],
            UnlockRule.from_pace(self._content.plan_rules().pace),
        )
        return subscription


class StartDemoSubscription:
    """`POST /api/billing/demo`: consent required, no existing subscription, then start."""

    def __init__(self, uow: UnitOfWork, start: StartSubscription) -> None:
        self._uow = uow
        self._start = start

    async def execute(
        self, session: Session, auto_renew_consent: bool, plan_id: str | None
    ) -> Subscription:
        if not auto_renew_consent:
            raise ConsentRequired()
        async with self._uow:
            existing = await self._uow.subscriptions.get(session.id)
        if existing is not None and existing.status in STARTED_STATUSES:
            raise AlreadySubscribed()
        return await self._start.execute(
            session, StartRequest("demo", auto_renew_consent=True, plan_id=plan_id)
        )


class CheckAccess:
    """The access gate's logic: asks `Subscription.can_access()`; raises AccessDenied."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session) -> None:
        now = session.app_now(self._clock.now())
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
            has_plan = await self._uow.plans.get(session.id) is not None
        denied = subscription.can_access(now, has_plan)
        if denied is not None:
            raise denied
