"""`GET /api/app-copy`: the app strings, finished for this session. Read-only."""

from typing import Any

from app.application.ports import ContentProvider
from app.domain.app_copy.render import NEUTRAL_RECIPIENT_KEY, render_app_copy
from app.domain.session.entities import Session
from app.domain.shared.labels import with_display_name


class GetAppCopy:
    def __init__(self, content: ContentProvider) -> None:
        self._content = content

    async def execute(self, session: Session) -> dict[str, Any]:
        key = session.recipient_key or NEUTRAL_RECIPIENT_KEY
        labels = with_display_name(self._content.recipient_labels(key), session.display_name)
        return render_app_copy(self._content.app_copy(), labels)
