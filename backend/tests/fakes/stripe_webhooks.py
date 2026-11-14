"""FakeStripe: Stripe-shaped webhook events signed with a test secret (no network)."""

import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

TEST_WEBHOOK_SECRET = "whsec_test_not_a_real_secret"


class FakeStripe:
    """Emits signed webhook payloads: `(payload bytes, Stripe-Signature header value)`."""

    def __init__(self, secret: str = TEST_WEBHOOK_SECRET) -> None:
        self.secret = secret

    def sign(self, payload: bytes, secret: str | None = None, at: int | None = None) -> str:
        timestamp = at if at is not None else int(time.time())
        signed = f"{timestamp}.".encode() + payload
        digest = hmac.new(
            (self.secret if secret is None else secret).encode(), signed, hashlib.sha256
        ).hexdigest()
        return f"t={timestamp},v1={digest}"

    def event(
        self, event_type: str, obj: dict[str, Any], event_id: str | None = None
    ) -> tuple[bytes, str]:
        body = {
            "id": event_id or f"evt_{uuid4().hex}",
            "object": "event",
            "type": event_type,
            "data": {"object": obj},
        }
        payload = json.dumps(body).encode()
        return payload, self.sign(payload)

    # --- event builders (shapes follow the Stripe API objects) ----------------------------------

    def checkout_completed(
        self,
        session_id: UUID,
        customer: str,
        subscription: str,
        plan_id: str = "four_week",
        paid: bool = True,
        event_id: str | None = None,
    ) -> tuple[bytes, str]:
        return self.event(
            "checkout.session.completed",
            {
                "id": "cs_test_1",
                "object": "checkout.session",
                "status": "complete",
                "payment_status": "paid" if paid else "unpaid",
                "customer": customer,
                "subscription": subscription,
                "metadata": {"session_id": str(session_id), "plan_id": plan_id},
            },
            event_id,
        )

    def invoice_paid(
        self,
        customer: str,
        subscription: str,
        period_end: datetime,
        first: bool = False,
        session_id: UUID | None = None,
        event_id: str | None = None,
    ) -> tuple[bytes, str]:
        return self.event(
            "invoice.paid",
            self._invoice(customer, subscription, period_end, first, session_id),
            event_id,
        )

    def invoice_payment_failed(
        self,
        customer: str,
        subscription: str,
        period_end: datetime,
        session_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        return self.event(
            "invoice.payment_failed",
            self._invoice(customer, subscription, period_end, False, session_id),
        )

    @staticmethod
    def _invoice(
        customer: str,
        subscription: str,
        period_end: datetime,
        first: bool,
        session_id: UUID | None,
    ) -> dict[str, Any]:
        details: dict[str, Any] = {"subscription": subscription}
        if session_id is not None:
            details["metadata"] = {"session_id": str(session_id)}
        return {
            "id": f"in_{uuid4().hex}",
            "object": "invoice",
            "customer": customer,
            "billing_reason": "subscription_create" if first else "subscription_cycle",
            "parent": {"type": "subscription_details", "subscription_details": details},
            "lines": {"data": [{"period": {"end": int(period_end.timestamp())}}]},
        }

    def subscription_event(
        self,
        event_type: str,
        customer: str,
        subscription: str,
        session_id: UUID | None = None,
        cancel_at_period_end: bool = False,
    ) -> tuple[bytes, str]:
        obj: dict[str, Any] = {
            "id": subscription,
            "object": "subscription",
            "customer": customer,
            "cancel_at_period_end": cancel_at_period_end,
            "metadata": {"session_id": str(session_id)} if session_id else {},
        }
        return self.event(event_type, obj)

    def test_clock_ready(self) -> tuple[bytes, str]:
        return self.event(
            "test_helpers.test_clock.ready",
            {"id": "clock_fake_1", "object": "test_helpers.test_clock", "status": "ready"},
        )
