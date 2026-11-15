"""Use cases: read the quick guides (public; a session only personalises the wording)."""

from app.application.ports import ContentProvider
from app.domain.guides.entities import RenderedGuide
from app.domain.guides.render import render_guide
from app.domain.session.entities import Session
from app.domain.shared.labels import RecipientLabels

# Labels before the quiz (or with no session): the neutral recipient.
NEUTRAL_RECIPIENT_KEY = "other"


def _labels(content: ContentProvider, session: Session | None) -> RecipientLabels:
    """Singular labels (as in the lessons); no subscription or plan is looked at."""
    key = (session.recipient_key if session else None) or NEUTRAL_RECIPIENT_KEY
    return content.lesson_recipient_labels(key, session.display_name if session else None)


class ListGuides:
    def __init__(self, content: ContentProvider) -> None:
        self._content = content

    def execute(self, session: Session | None) -> list[RenderedGuide]:
        book = self._content.quick_guides()
        labels = _labels(self._content, session)
        return [render_guide(book, g, labels) for g in book.guides]


class GetGuide:
    def __init__(self, content: ContentProvider) -> None:
        self._content = content

    def execute(self, guide_id: str, session: Session | None) -> RenderedGuide:
        book = self._content.quick_guides()
        return render_guide(book, book.get(guide_id), _labels(self._content, session))
