"""Stripe webhook verification and mapping to `BillingEvent` (the only reader of raw events)."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import stripe

from app.application.billing.events import (
    CHECKOUT_COMPLETED,
    INVOICE_PAID,
    INVOICE_PAYMENT_FAILED,
    SUBSCRIPTION_DELETED,
    SUBSCRIPTION_UPDATED,
    TEST_CLOCK_READY,
    BillingEvent,
)
from app.domain.billing.errors import InvalidWebhookSignature

SIGNATURE_TOLERANCE_SECONDS = 300


def _uuid_or_none(value: object) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except ValueError:
        return None


def _id_of(value: Any) -> str | None:
    """An id from a string or an expanded object."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return str(value["id"])
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _metadata_session_id(obj: dict[str, Any]) -> UUID | None:
    """`session_id` from the object's metadata, or from where an invoice carries the
    subscription metadata (`subscription_details`, `parent.subscription_details`, line items)."""
    candidates: list[dict[str, Any]] = [
        _dict(obj.get("metadata")),
        _dict(_dict(obj.get("subscription_details")).get("metadata")),
        _dict(_dict(_dict(obj.get("parent")).get("subscription_details")).get("metadata")),
    ]
    lines = _dict(obj.get("lines")).get("data")
    if isinstance(lines, list):
        candidates += [_dict(_dict(line).get("metadata")) for line in lines]
    for metadata in candidates:
        found = _uuid_or_none(metadata.get("session_id"))
        if found is not None:
            return found
    return None


def _plan_id(obj: dict[str, Any]) -> str | None:
    value = _dict(obj.get("metadata")).get("plan_id")
    return value if isinstance(value, str) else None


def _invoice_subscription_id(obj: dict[str, Any]) -> str | None:
    found = _id_of(obj.get("subscription"))
    if found:
        return found
    details = _dict(_dict(obj.get("parent")).get("subscription_details"))
    return _id_of(details.get("subscription"))


def _invoice_period_end(obj: dict[str, Any]) -> datetime | None:
    lines = _dict(obj.get("lines")).get("data")
    if isinstance(lines, list) and lines:
        end = _dict(_dict(lines[0]).get("period")).get("end")
        if isinstance(end, int):
            return datetime.fromtimestamp(end, UTC)
    return None


class StripeWebhookParser:
    """Checks the `Stripe-Signature` header against the webhook secret, then maps the event.

    An empty secret rejects everything (never verify against an empty key).
    """

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def parse(self, payload: bytes, signature: str | None) -> BillingEvent:
        if not self._secret or not signature:
            raise InvalidWebhookSignature()
        try:
            stripe.WebhookSignature.verify_header(
                payload.decode("utf-8"), signature, self._secret, SIGNATURE_TOLERANCE_SECONDS
            )
            raw = json.loads(payload)
        except (stripe.SignatureVerificationError, ValueError) as exc:
            raise InvalidWebhookSignature() from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
            raise InvalidWebhookSignature()
        event_type = str(raw.get("type", ""))
        obj = _dict(_dict(raw.get("data")).get("object"))
        return self._map(str(raw["id"]), event_type, obj)

    @staticmethod
    def _map(event_id: str, event_type: str, obj: dict[str, Any]) -> BillingEvent:
        customer_id = _id_of(obj.get("customer"))
        session_id = _metadata_session_id(obj)
        if event_type == CHECKOUT_COMPLETED:
            return BillingEvent(
                event_id,
                event_type,
                session_id=session_id,
                customer_id=customer_id,
                subscription_id=_id_of(obj.get("subscription")),
                plan_id=_plan_id(obj),
                paid=obj.get("status") == "complete"
                and obj.get("payment_status") in ("paid", "no_payment_required"),
            )
        if event_type in (INVOICE_PAID, INVOICE_PAYMENT_FAILED):
            return BillingEvent(
                event_id,
                event_type,
                session_id=session_id,
                customer_id=customer_id,
                subscription_id=_invoice_subscription_id(obj),
                first_payment=obj.get("billing_reason") == "subscription_create",
                period_end=_invoice_period_end(obj),
            )
        if event_type in (SUBSCRIPTION_UPDATED, SUBSCRIPTION_DELETED):
            return BillingEvent(
                event_id,
                event_type,
                session_id=session_id,
                customer_id=customer_id,
                subscription_id=_id_of(obj.get("id")),
                plan_id=_plan_id(obj),
                cancel_at_period_end=obj.get("cancel_at_period_end") is True,
            )
        if event_type == TEST_CLOCK_READY:
            return BillingEvent(event_id, event_type, test_clock_id=_id_of(obj))
        return BillingEvent(event_id, event_type)
