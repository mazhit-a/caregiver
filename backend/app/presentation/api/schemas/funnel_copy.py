from app.presentation.api.schemas.base import CamelModel


class TextSegmentOut(CamelModel):
    text: str
    strong: bool


class LoaderCopyOut(CamelModel):
    title: str


class PlanPreviewCopyOut(CamelModel):
    title: str
    cta: str
    highlight_label: str


class QuizCopyOut(CamelModel):
    health_note: str


class PaywallStatesOut(CamelModel):
    success: str
    returned_canceled: str


class PaywallPlanOut(CamelModel):
    id: str
    label: str
    price_today: str
    detail: str
    disclosure: list[TextSegmentOut]
    consent_label: str
    pay_button_label: str
    first_renewal_date: str


class PaywallCopyOut(CamelModel):
    headline: str
    subhead: str
    includes: list[str]
    consent_required_error: str
    states: PaywallStatesOut
    default_plan_id: str
    plans: list[PaywallPlanOut]


class FunnelCopyResponse(CamelModel):
    quiz: QuizCopyOut
    loader: LoaderCopyOut
    plan_preview: PlanPreviewCopyOut
    paywall: PaywallCopyOut
