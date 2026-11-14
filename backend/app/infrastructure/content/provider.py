"""ContentProvider adapter over the loaded content bundle."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.domain.safety.resources import CrisisResource
from app.domain.shared.errors import DomainError
from app.domain.shared.labels import RecipientLabels, lesson_labels, render_text
from app.infrastructure.content.loader import ContentBundle, load_content
from app.infrastructure.content.schemas import LessonFile

_AUTHORING_KEYS = frozenset({"notes"})


class UnknownContentReference(DomainError):
    """A lesson, recipient key or variant that the content does not define."""

    code = "unknown_content_reference"


class JsonContentProvider:
    """Implements the `ContentProvider` port from validated JSON content."""

    def __init__(self, bundle: ContentBundle) -> None:
        self._bundle = bundle
        self._labels = {
            key: RecipientLabels.from_mapping(model.model_dump(by_alias=True))
            for key, model in bundle.quiz.recipient_labels.items()
        }

    @classmethod
    def from_directory(cls, content_dir: Path) -> "JsonContentProvider":
        return cls(load_content(content_dir))

    @property
    def content_version(self) -> str:
        return self._bundle.content_version

    def recipient_keys(self) -> list[str]:
        return list(self._labels)

    def recipient_labels(self, key: str) -> RecipientLabels:
        if key not in self._labels:
            raise UnknownContentReference(f"Unknown recipient key '{key}'", {"key": key})
        return self._labels[key]

    def lesson_recipient_labels(self, key: str) -> RecipientLabels:
        self.recipient_labels(key)  # validates the key
        return lesson_labels(key, self._labels)

    def crisis_resources(self) -> list[CrisisResource]:
        return [
            CrisisResource(id=r.id, name=r.name, phone=r.phone, description=r.description)
            for r in self._bundle.crisis_resources.resources
        ]

    def crisis_resources_need_verification(self) -> bool:
        return self._bundle.crisis_resources.verify_before_launch

    def lesson_ids(self) -> list[str]:
        return sorted(self._bundle.lessons)

    def lesson_variants(self, lesson_id: str) -> list[str]:
        return self._lesson(lesson_id).variant_ids()

    def render_lesson(
        self,
        lesson_id: str,
        recipient_key: str,
        variant: str | None = None,
        runtime_values: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Lesson as camelCase JSON data with every placeholder filled (authoring notes dropped).

        Runtime placeholders ({savedPhrase}, {firstScore}, ...) must be supplied by the caller;
        a placeholder without a value raises. Variant maps are left for the lesson use case.
        """
        lesson = self._lesson(lesson_id)
        variants = lesson.variant_ids()
        if variant is not None and variant not in variants:
            raise UnknownContentReference(
                f"Lesson '{lesson_id}' has no variant '{variant}'",
                {"lesson": lesson_id, "variant": variant},
            )
        labels = self.lesson_recipient_labels(recipient_key)
        data = lesson.model_dump(by_alias=True, mode="json", exclude_none=True)
        return {
            key: _render_tree(value, labels, runtime_values)
            for key, value in data.items()
            if key not in _AUTHORING_KEYS
        }

    def _lesson(self, lesson_id: str) -> LessonFile:
        if lesson_id not in self._bundle.lessons:
            raise UnknownContentReference(f"Unknown lesson '{lesson_id}'", {"lesson": lesson_id})
        return self._bundle.lessons[lesson_id]


def _render_tree(node: Any, labels: RecipientLabels, extra: Mapping[str, str] | None) -> Any:
    if isinstance(node, str):
        return render_text(node, labels, extra)
    if isinstance(node, list):
        return [_render_tree(item, labels, extra) for item in node]
    if isinstance(node, dict):
        return {key: _render_tree(value, labels, extra) for key, value in node.items()}
    return node
