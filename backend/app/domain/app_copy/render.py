"""Renders the app strings (content/app-copy.json) with the recipient labels. Pure."""

from collections.abc import Mapping
from typing import Any

from app.domain.shared.labels import RecipientLabels, render_text

AppCopy = Mapping[str, Any]
"""Section name -> text name -> text (placeholders unfilled). A text may also be a nested
mapping of texts (the lesson labels)."""

# Labels used before the quiz is finished (no recipient chosen yet).
NEUTRAL_RECIPIENT_KEY = "other"


def _render(node: Any, labels: RecipientLabels) -> Any:
    if isinstance(node, str):
        return render_text(node, labels)
    return {name: _render(child, labels) for name, child in node.items()}


def render_app_copy(copy: AppCopy, labels: RecipientLabels) -> dict[str, Any]:
    return {section: _render(texts, labels) for section, texts in copy.items()}
