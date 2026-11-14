"""Renders the app strings (content/app-copy.json) with the recipient labels. Pure."""

from collections.abc import Mapping

from app.domain.shared.labels import RecipientLabels, render_text

AppCopy = Mapping[str, Mapping[str, str]]
"""Section name -> text name -> text (placeholders unfilled)."""

# Labels used before the quiz is finished (no recipient chosen yet).
NEUTRAL_RECIPIENT_KEY = "other"


def render_app_copy(copy: AppCopy, labels: RecipientLabels) -> dict[str, dict[str, str]]:
    return {
        section: {name: render_text(text, labels) for name, text in texts.items()}
        for section, texts in copy.items()
    }
