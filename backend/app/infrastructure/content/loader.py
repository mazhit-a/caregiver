"""Loads and validates every content file once; computes the content version hash."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.infrastructure.content.lesson_validation import validate_lesson
from app.infrastructure.content.schemas import (
    AppCopyFile,
    CrisisResourcesFile,
    FunnelCopyFile,
    LessonFile,
    PhrasesFile,
    PlanRulesFile,
    PricingFile,
    QuickGuidesFile,
    QuizFile,
    SafetyTermsFile,
    VisitQuestionsFile,
)

_SINGLE_FILES = (
    "app-copy.json",
    "quiz.json",
    "plan-rules.json",
    "phrases.json",
    "pricing.json",
    "funnel-copy.json",
    "safety-terms.json",
    "crisis-resources.json",
    "visit-questions.json",
    "quick-guides.json",
)
_LESSONS_DIR = "lessons"


class ContentLoadError(Exception):
    """Content is missing or invalid; the message names the file and the field path."""


@dataclass(frozen=True)
class ContentBundle:
    app_copy: AppCopyFile
    quiz: QuizFile
    plan_rules: PlanRulesFile
    phrases: PhrasesFile
    pricing: PricingFile
    funnel_copy: FunnelCopyFile
    safety_terms: SafetyTermsFile
    crisis_resources: CrisisResourcesFile
    visit_questions: VisitQuestionsFile
    quick_guides: QuickGuidesFile
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
            problems = validate_lesson(lesson)
            if problems:
                detail = "; ".join(f"{path}: {message}" for path, message in problems[:10])
                raise ContentLoadError(f"{name}: {detail}")
            lessons[lesson.id] = lesson
    return ContentBundle(
        app_copy=_parse("app-copy.json", raw["app-copy.json"], AppCopyFile),
        quiz=_parse("quiz.json", raw["quiz.json"], QuizFile),
        plan_rules=_parse("plan-rules.json", raw["plan-rules.json"], PlanRulesFile),
        phrases=_parse("phrases.json", raw["phrases.json"], PhrasesFile),
        pricing=_parse("pricing.json", raw["pricing.json"], PricingFile),
        funnel_copy=_parse("funnel-copy.json", raw["funnel-copy.json"], FunnelCopyFile),
        safety_terms=_parse("safety-terms.json", raw["safety-terms.json"], SafetyTermsFile),
        crisis_resources=_parse(
            "crisis-resources.json", raw["crisis-resources.json"], CrisisResourcesFile
        ),
        visit_questions=_parse(
            "visit-questions.json", raw["visit-questions.json"], VisitQuestionsFile
        ),
        quick_guides=_parse("quick-guides.json", raw["quick-guides.json"], QuickGuidesFile),
        lessons=lessons,
        content_version=compute_content_version(raw),
    )
