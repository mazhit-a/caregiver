"""quick-guides.json (validated models) -> the guides domain objects."""

from app.domain.guides.entities import (
    GuideCommon,
    GuideResource,
    GuideSource,
    GuideStep,
    QuickGuide,
    QuickGuideBook,
)
from app.infrastructure.content.schemas import QuickGuidesFile


def to_quick_guide_book(file: QuickGuidesFile) -> QuickGuideBook:
    c = file.common
    return QuickGuideBook(
        common=GuideCommon(
            footer=c.footer,
            call_now_title=c.call_now_title,
            steps_title=c.steps_title,
            then_title=c.then_title,
            dont_title=c.dont_title,
            resources_title=c.resources_title,
        ),
        resources={
            rid: GuideResource(r.label, r.number, r.tel) for rid, r in file.resources.items()
        },
        guides=tuple(
            QuickGuide(
                id=g.id,
                title=g.title,
                summary=g.summary,
                urgency=g.urgency,
                call_now=tuple(g.call_now),
                steps=tuple(GuideStep(s.title, s.text) for s in g.steps),
                then=tuple(g.then),
                dont=tuple(g.dont),
                resources=tuple(g.resources),
                sources=tuple(GuideSource(s.name, s.url) for s in g.sources),
            )
            for g in file.guides
        ),
    )
