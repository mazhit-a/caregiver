"""The wording of the pre-subscription funnel (content/funnel-copy.json), placeholders unfilled."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FunnelCopy:
    loader_title: str
    plan_preview_title: str
    plan_preview_cta: str
    highlight_label: str
    health_note: str
    paywall_headline: str
    paywall_includes: tuple[str, ...]
    money_format: str
    plan_detail: str
    disclosure: str
    consent_checkbox: str
    consent_required_error: str
    pay_button: str
    success: str
    returned_canceled: str
