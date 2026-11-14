"""`PaymentGateway` on the Stripe SDK (test mode). The only place that imports `stripe`."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import UUID

import stripe

from app.application.billing.payments import (
    CheckoutRequest,
    CheckoutSessionInfo,
    CheckoutSessionRef,
    CustomerRef,
)
from app.domain.billing.errors import PaymentGatewayError

_T = TypeVar("_T")

# Stripe's test payment method that attaches fine and is declined when charged.
FAILING_TEST_PAYMENT_METHOD = "pm_card_chargeCustomerFail"


def _timestamp(value: datetime) -> int:
    return int(value.timestamp())


def _period_end(subscription: Any) -> datetime | None:
    """The current period end: on the subscription, or (newer API versions) on its first item."""
    if subscription is None or isinstance(subscription, str):
        return None
    value = subscription.get("current_period_end")
    if value is None:
        items = (subscription.get("items") or {}).get("data") or []
        value = items[0].get("current_period_end") if items else None
    return datetime.fromtimestamp(value, UTC) if value else None


def _uuid_or_none(value: str | None) -> UUID | None:
    try:
        return UUID(value) if value else None
    except ValueError:
        return None


def _id_of(value: Any) -> str | None:
    """An id from an expandable field (a string id or an expanded object)."""
    if value is None:
        return None
    return value if isinstance(value, str) else str(value["id"])


class StripePaymentGateway:
    """Sync SDK calls run in a worker thread; every SDK error becomes `PaymentGatewayError`."""

    def __init__(self, client: stripe.StripeClient) -> None:
        self._v1 = client.v1

    @classmethod
    def from_api_key(cls, api_key: str) -> "StripePaymentGateway":
        return cls(stripe.StripeClient(api_key))

    @staticmethod
    async def _call(fn: Callable[[], _T]) -> _T:
        try:
            return await asyncio.to_thread(fn)
        except stripe.StripeError as exc:
            raise PaymentGatewayError() from exc

    async def create_customer(self, session_id: UUID, clock_frozen_at: datetime) -> CustomerRef:
        clock = await self._call(
            lambda: self._v1.test_helpers.test_clocks.create(
                params={"frozen_time": _timestamp(clock_frozen_at)}
            )
        )
        customer = await self._call(
            lambda: self._v1.customers.create(
                params={"test_clock": clock.id, "metadata": {"session_id": str(session_id)}}
            )
        )
        return CustomerRef(customer_id=customer.id, test_clock_id=clock.id)

    async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSessionRef:
        metadata = {
            "session_id": str(request.session_id),
            "plan_id": request.plan_id,
            "amount": str(request.amount_today),
        }
        created = await self._call(
            lambda: self._v1.checkout.sessions.create(
                params={
                    "mode": "subscription",
                    "customer": request.customer_id,
                    "line_items": [{"price": request.price_id, "quantity": 1}],
                    "discounts": [{"coupon": request.coupon_id}],
                    "success_url": request.success_url,
                    "cancel_url": request.cancel_url,
                    "metadata": metadata,
                    "subscription_data": {
                        "metadata": {
                            "session_id": metadata["session_id"],
                            "plan_id": request.plan_id,
                        }
                    },
                }
            )
        )
        if not created.url:
            raise PaymentGatewayError()
        return CheckoutSessionRef(id=created.id, url=created.url)

    async def retrieve_checkout_session(self, checkout_id: str) -> CheckoutSessionInfo:
        found = await self._call(
            lambda: self._v1.checkout.sessions.retrieve(
                checkout_id, params={"expand": ["subscription"]}
            )
        )
        data: dict[str, Any] = found.to_dict()
        metadata: dict[str, str] = data.get("metadata") or {}
        paid = data.get("status") == "complete" and data.get("payment_status") in (
            "paid",
            "no_payment_required",
        )
        return CheckoutSessionInfo(
            id=found.id,
            session_id=_uuid_or_none(metadata.get("session_id")),
            plan_id=metadata.get("plan_id"),
            paid=paid,
            customer_id=_id_of(data.get("customer")),
            subscription_id=_id_of(data.get("subscription")),
            period_end=_period_end(data.get("subscription")),
        )

    async def cancel_at_period_end(self, subscription_id: str) -> None:
        await self._call(
            lambda: self._v1.subscriptions.update(
                subscription_id, params={"cancel_at_period_end": True}
            )
        )

    async def cancel_now(self, subscription_id: str) -> None:
        await self._call(lambda: self._v1.subscriptions.cancel(subscription_id))

    async def advance_test_clock(self, test_clock_id: str, to: datetime) -> None:
        await self._call(
            lambda: self._v1.test_helpers.test_clocks.advance(
                test_clock_id, params={"frozen_time": _timestamp(to)}
            )
        )

    async def attach_failing_payment_method(self, customer_id: str) -> None:
        method = await self._call(
            lambda: self._v1.payment_methods.attach(
                FAILING_TEST_PAYMENT_METHOD, params={"customer": customer_id}
            )
        )
        await self._call(
            lambda: self._v1.customers.update(
                customer_id, params={"invoice_settings": {"default_payment_method": method.id}}
            )
        )
