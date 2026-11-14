"""The subscription state machine. Every status change goes through this entity."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from app.domain.billing.errors import AccessDenied, ConsentRequired, InvalidTransition

SubscriptionStatus = Literal["none", "active", "demo", "past_due", "canceling", "canceled", "ended"]
SubscriptionSource = Literal["demo", "stripe"]

ALL_STATUSES: tuple[SubscriptionStatus, ...] = (
    "none",
    "active",
    "demo",
    "past_due",
    "canceling",
    "canceled",
    "ended",
)

# TASK.md 6.6: none -> active|demo; active -> past_due -> active|canceled;
# active|demo -> canceling -> canceled (at period end); any -> ended (gentle exit).
# Deliberate addition: a Stripe `customer.subscription.deleted` event ends a Stripe subscription
# at once, so active|past_due|canceling -> canceled is legal too (`cancel_now`).
TRANSITIONS: dict[SubscriptionStatus, frozenset[SubscriptionStatus]] = {
    "none": frozenset({"active", "demo", "ended"}),
    "active": frozenset({"past_due", "canceling", "canceled", "ended"}),
    "demo": frozenset({"canceling", "ended"}),
    "past_due": frozenset({"active", "canceled", "ended"}),
    "canceling": frozenset({"canceled", "ended"}),
    "canceled": frozenset({"ended"}),
    "ended": frozenset(),
}

# Statuses of a subscription that was started (anything but `none`).
STARTED_STATUSES: frozenset[SubscriptionStatus] = frozenset(ALL_STATUSES) - {"none"}


@dataclass(frozen=True)
class SubscriptionHistoryEntry:
    """One status change (or period roll) with the app time it happened at."""

    session_id: UUID
    at: datetime  # app time, never wall-clock
    from_status: SubscriptionStatus
    to_status: SubscriptionStatus
    event: str  # e.g. started, renewed, demo_renewed, payment_failed, cancel_requested
    source: str  # demo | stripe | system | ...


@dataclass
class Subscription:
    session_id: UUID
    status: SubscriptionStatus = "none"
    plan_id: str | None = None
    source: SubscriptionSource | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    renewal_count: int = 0
    auto_renew_consent_at: datetime | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    _pending: list[SubscriptionHistoryEntry] = field(default_factory=list, repr=False)

    # --- consent -------------------------------------------------------------------------------

    def record_consent(self, at: datetime) -> None:
        """Store the auto-renew consent (first one wins). Must happen before a start."""
        if self.auto_renew_consent_at is None:
            self.auto_renew_consent_at = at

    # --- transitions ---------------------------------------------------------------------------

    @staticmethod
    def can_transition(current: SubscriptionStatus, target: SubscriptionStatus) -> bool:
        return target in TRANSITIONS[current]

    def transition(
        self, target: SubscriptionStatus, at: datetime, event: str, source: str | None = None
    ) -> None:
        """Move to `target` if the table allows it and record history. Raises InvalidTransition.

        Low-level: the named methods below are the API; this is shared by them.
        """
        if not self.can_transition(self.status, target):
            raise InvalidTransition(
                f"Cannot change a subscription from '{self.status}' to '{target}'.",
                {"from": self.status, "to": target},
            )
        self._pending.append(
            SubscriptionHistoryEntry(
                self.session_id, at, self.status, target, event, source or self.source or "system"
            )
        )
        self.status = target

    def start_demo(self, at: datetime, plan_id: str, period_days: int) -> None:
        if self.auto_renew_consent_at is None:
            raise ConsentRequired()
        self.transition("demo", at, "started", "demo")
        self.source = "demo"
        self.plan_id = plan_id
        self.current_period_start = at
        self.current_period_end = at + timedelta(days=period_days)

    def start_stripe(
        self,
        at: datetime,
        plan_id: str,
        period_end: datetime,
        customer_id: str | None = None,
        subscription_id: str | None = None,
    ) -> None:
        if self.auto_renew_consent_at is None:
            raise ConsentRequired()
        self.transition("active", at, "started", "stripe")
        self.source = "stripe"
        self.plan_id = plan_id
        self.current_period_start = at
        self.current_period_end = period_end
        self.stripe_customer_id = customer_id
        self.stripe_subscription_id = subscription_id

    def renew(
        self, at: datetime, period_end: datetime, event: str = "renewed", source: str | None = None
    ) -> None:
        """A paid (or simulated) renewal: roll the period and count it.

        `active` and `demo` keep their status (the history entry has from == to);
        `past_due` becomes `active`. Anything else raises InvalidTransition.
        """
        if self.status == "past_due":
            self.transition("active", at, event, source)
        elif self.status in ("active", "demo"):
            self._pending.append(
                SubscriptionHistoryEntry(
                    self.session_id,
                    at,
                    self.status,
                    self.status,
                    event,
                    source or self.source or "system",
                )
            )
        else:
            raise InvalidTransition(
                f"Cannot renew a subscription that is '{self.status}'.",
                {"from": self.status, "to": self.status},
            )
        self.current_period_start = self.current_period_end or at
        self.current_period_end = period_end
        self.renewal_count += 1

    def mark_past_due(self, at: datetime, source: str | None = None) -> None:
        self.transition("past_due", at, "payment_failed", source)

    def cancel_at_period_end(self, at: datetime, source: str | None = None) -> None:
        self.transition("canceling", at, "cancel_requested", source)

    def end_period(self, at: datetime, source: str | None = None) -> None:
        """The period ended for a `canceling` subscription (or a past-due one gave up)."""
        self.transition("canceled", at, "period_ended", source)

    def cancel_now(self, at: datetime, source: str | None = None) -> None:
        """The provider deleted the subscription: active|past_due|canceling -> canceled."""
        self.transition("canceled", at, "subscription_deleted", source)

    def end_now(self, at: datetime, source: str | None = None) -> None:
        """Gentle exit: from any status to `ended`."""
        self.transition("ended", at, "ended", source)

    def pull_history(self) -> list[SubscriptionHistoryEntry]:
        """The history entries recorded since the last pull (the repository persists them)."""
        entries, self._pending = self._pending, []
        return entries

    # --- access gate ---------------------------------------------------------------------------

    def can_access(self, at: datetime, has_plan: bool) -> AccessDenied | None:
        """None when app endpoints are allowed, else the `AccessDenied` to raise.

        `has_plan` only matters for `none` (no_plan vs no_subscription).
        """
        status = self.status
        if status in ("active", "demo"):
            return None
        if status == "canceling":
            if self.current_period_end is not None and at < self.current_period_end:
                return None
            return AccessDenied("no_subscription")
        if status == "none":
            return AccessDenied("no_subscription" if has_plan else "no_plan")
        if status == "past_due":
            return AccessDenied("past_due")
        if status == "canceled":
            return AccessDenied("no_subscription")
        return AccessDenied("ended")
