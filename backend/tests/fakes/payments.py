"""Fakes for the payment gateway port and the Stripe SDK boundary (no network)."""

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl
from uuid import UUID

import stripe
from stripe import HTTPClient

from app.application.billing.payments import (
    CheckoutRequest,
    CheckoutSessionInfo,
    CheckoutSessionRef,
    CustomerRef,
)
from app.domain.billing.errors import PaymentGatewayError


class FakePaymentGateway:
    """In-memory `PaymentGateway` recording every call; `pay()` simulates the user paying."""

    def __init__(self) -> None:
        self.customers: list[tuple[UUID, datetime]] = []  # (session_id, clock_frozen_at)
        self.checkout_requests: list[CheckoutRequest] = []
        self.retrieved: list[str] = []
        self.calls: list[tuple[str, Any]] = []
        self.sessions: dict[str, CheckoutSessionInfo] = {}
        self.fail_with: PaymentGatewayError | None = None
        self.period_end = datetime(2026, 2, 2, 9, 0, tzinfo=UTC)

    def _maybe_fail(self) -> None:
        if self.fail_with is not None:
            raise self.fail_with

    async def create_customer(self, session_id: UUID, clock_frozen_at: datetime) -> CustomerRef:
        self._maybe_fail()
        self.customers.append((session_id, clock_frozen_at))
        n = len(self.customers)
        return CustomerRef(customer_id=f"cus_fake_{n}", test_clock_id=f"clock_fake_{n}")

    async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSessionRef:
        self._maybe_fail()
        self.checkout_requests.append(request)
        checkout_id = f"cs_test_fake_{len(self.checkout_requests)}"
        self.sessions[checkout_id] = CheckoutSessionInfo(
            id=checkout_id,
            session_id=request.session_id,
            plan_id=request.plan_id,
            paid=False,
            customer_id=request.customer_id,
            subscription_id=None,
            period_end=None,
        )
        return CheckoutSessionRef(id=checkout_id, url=f"https://checkout.stripe.test/{checkout_id}")

    async def retrieve_checkout_session(self, checkout_id: str) -> CheckoutSessionInfo:
        self._maybe_fail()
        self.retrieved.append(checkout_id)
        if checkout_id not in self.sessions:
            raise PaymentGatewayError()
        return self.sessions[checkout_id]

    async def cancel_at_period_end(self, subscription_id: str) -> None:
        self._maybe_fail()
        self.calls.append(("cancel_at_period_end", subscription_id))

    async def cancel_now(self, subscription_id: str) -> None:
        self._maybe_fail()
        self.calls.append(("cancel_now", subscription_id))

    async def advance_test_clock(self, test_clock_id: str, to: datetime) -> None:
        self._maybe_fail()
        self.calls.append(("advance_test_clock", (test_clock_id, to)))

    async def attach_failing_payment_method(self, customer_id: str) -> None:
        self._maybe_fail()
        self.calls.append(("attach_failing_payment_method", customer_id))

    def pay(self, checkout_id: str) -> None:
        """Mark the checkout paid, as Stripe does once the customer completes it."""
        info = self.sessions[checkout_id]
        self.sessions[checkout_id] = CheckoutSessionInfo(
            id=info.id,
            session_id=info.session_id,
            plan_id=info.plan_id,
            paid=True,
            customer_id=info.customer_id,
            subscription_id=f"sub_fake_{checkout_id}",
            period_end=self.period_end,
        )


class RecordingStripeHttpClient(HTTPClient):
    """Stripe SDK HTTP boundary: records requests, answers from canned JSON, never networks."""

    name = "recording-fake"

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[tuple[str, str, dict[str, str]]] = []  # method, path, form fields
        self.checkout_session: dict[str, Any] = {}
        self.error: tuple[int, dict[str, Any]] | None = None

    def request(  # type: ignore[no-untyped-def]
        self, method, url, headers, post_data=None, *, _usage=None
    ):
        raise NotImplementedError

    def request_with_retries(  # type: ignore[no-untyped-def]
        self, method, url, headers, post_data=None, max_network_retries=None, *, _usage=None
    ):
        path = url.split("stripe.com", 1)[1].split("?")[0]
        fields = dict(parse_qsl(post_data or "", keep_blank_values=True))
        if "?" in url:
            fields.update(parse_qsl(url.split("?", 1)[1]))
        self.requests.append((method.upper(), path, fields))
        if self.error is not None:
            status, body = self.error
            return json.dumps(body), status, {}
        return json.dumps(self._answer(method.upper(), path)), 200, {}

    def request_stream(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def close(self) -> None:
        return None

    def _answer(self, method: str, path: str) -> Mapping[str, Any]:
        if path == "/v1/test_helpers/test_clocks":
            return {"id": "clock_1", "object": "test_helpers.test_clock"}
        if path == "/v1/customers":
            return {"id": "cus_1", "object": "customer"}
        if path == "/v1/checkout/sessions":
            return {"id": "cs_test_1", "object": "checkout.session", "url": "https://pay.test/cs"}
        if path.startswith("/v1/checkout/sessions/"):
            return {
                "id": path.rsplit("/", 1)[1],
                "object": "checkout.session",
                **self.checkout_session,
            }
        if path.startswith("/v1/test_helpers/test_clocks/"):
            return {"id": "clock_1", "object": "test_helpers.test_clock"}
        if path == "/v1/payment_methods/pm_card_chargeCustomerFail/attach":
            return {"id": "pm_1", "object": "payment_method"}
        return {"id": "x", "object": "thing"}

    def fields(self, path: str) -> dict[str, str]:
        """The form fields of the single request to `path`."""
        matching = [f for _, p, f in self.requests if p == path]
        assert len(matching) == 1, self.requests
        return matching[0]


def stripe_client_with(http: HTTPClient) -> stripe.StripeClient:
    return stripe.StripeClient("sk_test_fake", http_client=http)
