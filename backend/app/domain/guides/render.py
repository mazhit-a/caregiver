"""Renders quick guides with the recipient labels (the only fill is `render_text`). Pure."""

from app.domain.guides.entities import (
    GuideStep,
    QuickGuide,
    QuickGuideBook,
    RenderedGuide,
)
from app.domain.shared.labels import RecipientLabels, render_text


def render_guide(book: QuickGuideBook, guide: QuickGuide, labels: RecipientLabels) -> RenderedGuide:
    def fill(text: str) -> str:
        return render_text(text, labels)

    common = book.common
    return RenderedGuide(
        id=guide.id,
        title=fill(guide.title),
        summary=fill(guide.summary),
        urgency=guide.urgency,
        call_now_title=common.call_now_title,
        call_now=tuple(fill(t) for t in guide.call_now),
        steps_title=common.steps_title,
        steps=tuple(GuideStep(fill(s.title), fill(s.text)) for s in guide.steps),
        then_title=common.then_title,
        then=tuple(fill(t) for t in guide.then),
        dont_title=common.dont_title,
        dont=tuple(fill(t) for t in guide.dont),
        resources_title=common.resources_title,
        resources=tuple(book.resources[rid] for rid in guide.resources),
        sources=guide.sources,
        footer=common.footer,
    )
