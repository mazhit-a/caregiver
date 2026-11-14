"""Recipient labels and placeholder rendering. The only place that fills `{...}` placeholders."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace

from app.domain.shared.errors import DomainError

_PLACEHOLDER = re.compile(r"\{([A-Za-z_]\w*)\}")

# Quiz key whose lessons use singular "your parent" labels (lesson notes in content/lessons).
_BOTH_KEY = "both"
_BOTH_LESSON_LABELS = {
    "recipient": "your parent",
    "possessive": "your parent's",
    "pronoun": "they",
    "object": "them",
    "was": "was",
    "is": "is",
    "has": "has",
    "lives": "lives",
}


class UnknownPlaceholder(DomainError):
    """A text uses a placeholder for which no value is known."""

    code = "unknown_placeholder"

    def __init__(self, name: str, text: str) -> None:
        super().__init__(f"Unknown placeholder {{{name}}}", {"placeholder": name, "text": text})
        self.name = name


@dataclass(frozen=True)
class RecipientLabels:
    """Words for the person being cared for (one entry of quiz.json recipientLabels)."""

    recipient: str
    possessive: str
    pronoun: str
    object: str
    was: str
    is_: str
    has: str
    lives: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, str]) -> "RecipientLabels":
        return cls(
            recipient=raw["recipient"],
            possessive=raw["possessive"],
            pronoun=raw["pronoun"],
            object=raw["object"],
            was=raw["was"],
            is_=raw["is"],
            has=raw["has"],
            lives=raw["lives"],
        )

    def placeholder_values(self) -> dict[str, str]:
        """Every supported placeholder, with the capitalised variants."""
        values = {
            "recipient": self.recipient,
            "possessive": self.possessive,
            "pronoun": self.pronoun,
            "object": self.object,
            "was": self.was,
            "is": self.is_,
            "has": self.has,
            "lives": self.lives,
        }
        for name in ("recipient", "possessive", "pronoun"):
            values[name.capitalize()] = _capitalize(values[name])
        return values


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def with_display_name(labels: RecipientLabels, display_name: str | None) -> RecipientLabels:
    """The onboarding / profile name replaces `{recipient}` and `{possessive}` ("Margaret",
    "Margaret's"); pronouns and verbs stay. No name leaves the labels unchanged."""
    if not display_name:
        return labels
    return replace(labels, recipient=display_name, possessive=f"{display_name}'s")


def lesson_labels(key: str, labels_by_key: Mapping[str, RecipientLabels]) -> RecipientLabels:
    """Labels for lessons: lessons talk about one person, so `both` becomes "your parent"."""
    if key == _BOTH_KEY:
        return RecipientLabels.from_mapping(_BOTH_LESSON_LABELS)
    return labels_by_key[key]


def render_text(text: str, labels: RecipientLabels, extra: Mapping[str, str] | None = None) -> str:
    """Fill placeholders from the labels and `extra`; an unknown placeholder raises."""
    values = {**labels.placeholder_values(), **(extra or {})}

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise UnknownPlaceholder(name, text)
        return values[name]

    return _PLACEHOLDER.sub(replace, text)


def render_tree(node: object, labels: RecipientLabels) -> object:
    """Fill placeholders in every string of a JSON-like tree (dicts, lists, strings)."""
    if isinstance(node, str):
        return render_text(node, labels)
    if isinstance(node, list):
        return [render_tree(item, labels) for item in node]
    if isinstance(node, dict):
        return {key: render_tree(value, labels) for key, value in node.items()}
    return node
