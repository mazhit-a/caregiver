"""Loads and validates every content file once; computes the content version hash."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.infrastructure.content.schemas import (
    FunnelCopyFile,
    LessonFile,
    PhrasesFile,
    PlanRulesFile,
    PricingFile,
    QuizFile,
)

_SINGLE_FILES = ("quiz.json", "plan-rules.json", "phrases.json", "pricing.json", "funnel-copy.json")
_LESSONS_DIR = "lessons"


class ContentLoadError(Exception):
    """Content is missing or invalid; the message names the file and the field path."""


@dataclass(frozen=True)
class ContentBundle:
    quiz: QuizFile
    plan_rules: PlanRulesFile
    phrases: PhrasesFile
    pricing: PricingFile
    funnel_copy: FunnelCopyFile
    lessons: dict[str, LessonFile]
    content_version: str


def _field_path(loc: tuple[int | str, ...]) -> str:
    return ".".join(str(part) for part in loc) or "<root>"


def _parse[M: BaseModel](name: str, raw: bytes, model: type[M]) -> M:
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContentLoadError(f"{name}: invalid JSON ({exc})") from exc
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{_field_path(err['loc'])}: {err['msg']}" for err in exc.errors()[:10]
        )
        raise ContentLoadError(f"{name}: {problems}") from exc


def _read(content_dir: Path, name: str) -> bytes:
    path = content_dir / name
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ContentLoadError(f"{name}: cannot read file in {content_dir} ({exc})") from exc


def content_files(content_dir: Path) -> list[str]:
    """Relative names of every content file that is loaded (and hashed), sorted."""
    lessons = sorted(
        f"{_LESSONS_DIR}/{p.name}" for p in (content_dir / _LESSONS_DIR).glob("*.json")
    )
    return [*sorted(_SINGLE_FILES), *lessons]


def compute_content_version(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(files[name])
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def load_content(content_dir: Path) -> ContentBundle:
    """Load all content files; raise ContentLoadError on the first invalid file."""
    if not content_dir.is_dir():
        raise ContentLoadError(f"content directory not found: {content_dir}")
    raw = {name: _read(content_dir, name) for name in content_files(content_dir)}
    lessons: dict[str, LessonFile] = {}
    for name in raw:
        if name.startswith(f"{_LESSONS_DIR}/"):
            lesson = _parse(name, raw[name], LessonFile)
            if f"{lesson.id}.json" != name.split("/", 1)[1]:
                raise ContentLoadError(f"{name}: id: lesson id '{lesson.id}' must match file name")
            lessons[lesson.id] = lesson
    return ContentBundle(
        quiz=_parse("quiz.json", raw["quiz.json"], QuizFile),
        plan_rules=_parse("plan-rules.json", raw["plan-rules.json"], PlanRulesFile),
        phrases=_parse("phrases.json", raw["phrases.json"], PhrasesFile),
        pricing=_parse("pricing.json", raw["pricing.json"], PricingFile),
        funnel_copy=_parse("funnel-copy.json", raw["funnel-copy.json"], FunnelCopyFile),
        lessons=lessons,
        content_version=compute_content_version(raw),
    )
