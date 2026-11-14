"""Result cache: a re-run calls the model only for what changed.

Key = (case id + case content hash, run index, config fingerprint). The fingerprint covers the
model, effort, thinking, harness, prompt version, the prompt FILE hash, the adapter's
`INPUT_FORMAT_NOTE` hash (only for versions that use it) and the parent model (only when set), so
editing any of them is a miss. What is cached is the parsed model
verdict (before `validate_verdict` and `apply_rules`), the call metrics and the wall time: domain
rules and graders are re-applied on every read, so a rule change needs no new model call.
Failed calls are never cached (retrying them is the point of a re-run).
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

from app.domain.roleplay.verdict import CoachVerdict, Goals
from app.infrastructure.llm.anthropic_coach import CallMetrics
from app.infrastructure.llm.prompt import INPUT_FORMAT_NOTE, PromptLoadError, uses_input_format_note
from evals.case import EvalCase
from evals.client import CoachConfig

DEFAULT_CACHE_DIR: Final = Path(__file__).resolve().parent / ".cache"
CACHE_FORMAT: Final = 1


def _sha(data: bytes | str) -> str:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()


def prompt_file_hash(content_dir: Path, version: str) -> str:
    path = content_dir / "prompts" / f"roleplay-turn.v{version}.md"
    if not path.is_file():
        raise PromptLoadError(f"Prompt file not found for version {version}: {path}")
    return _sha(path.read_bytes())


def fingerprint_parts(config: CoachConfig, content_dir: Path) -> dict[str, Any]:
    """Everything that changes what the model is asked. Also written into the report."""
    parts: dict[str, Any] = {
        "model": config.model,
        "effort": config.effort,
        "thinking": config.thinking,
        "harness": config.harness,
        "promptVersion": config.prompt_version,
        "promptFileSha256": prompt_file_hash(content_dir, config.prompt_version),
    }
    # Optional keys are written only when they apply, so a fingerprint (and every cached result)
    # of a config that does not use them stays byte-identical to what earlier runs produced.
    if uses_input_format_note(config.prompt_version):
        parts["inputFormatNoteSha256"] = _sha(INPUT_FORMAT_NOTE)
    if config.parent_model:
        parts["parentModel"] = config.parent_model
    return parts


def config_fingerprint(config: CoachConfig, content_dir: Path) -> str:
    canonical = json.dumps(fingerprint_parts(config, content_dir), sort_keys=True)
    return _sha(canonical)


@dataclass(frozen=True)
class CacheEntry:
    verdict: CoachVerdict
    wall_ms: float
    call: CallMetrics | None  # the headline record (aggregate when there are several calls)
    calls: tuple[CallMetrics, ...] = ()  # one per model call; empty for a single-call entry


def _to_json(entry: CacheEntry) -> dict[str, Any]:
    out: dict[str, Any] = {
        "format": CACHE_FORMAT,
        "verdict": asdict(entry.verdict),
        "wallMs": entry.wall_ms,
        "call": None if entry.call is None else asdict(entry.call),
    }
    if entry.calls:  # key absent for single-call entries: their files stay as before
        out["calls"] = [asdict(c) for c in entry.calls]
    return out


def _from_json(raw: dict[str, Any]) -> CacheEntry:
    v = raw["verdict"]
    verdict = CoachVerdict(
        goals=Goals(**v["goals"]),
        argued=v["argued"],
        flags=tuple(v["flags"]),
        tip=v["tip"],
        better_phrase=v["better_phrase"],
        parent_reaction=v["parent_reaction"],
        parent_mood=v["parent_mood"],
    )
    call = None if raw["call"] is None else CallMetrics(**raw["call"])
    calls = tuple(CallMetrics(**c) for c in raw.get("calls", ()))
    return CacheEntry(verdict, float(raw["wallMs"]), call, calls)


class ResultCache:
    """One JSON file per key under `<root>/<fingerprint[:16]>/`."""

    def __init__(self, root: Path = DEFAULT_CACHE_DIR) -> None:
        self._root = root

    def _path(self, case: EvalCase, run_index: int, fingerprint: str) -> Path:
        key = _sha(f"{case.id}|{_sha(case.to_json_line())}|{run_index}|{fingerprint}")
        return self._root / fingerprint[:16] / f"{key}.json"

    def has(self, case: EvalCase, run_index: int, fingerprint: str) -> bool:
        return self._path(case, run_index, fingerprint).is_file()

    def get(self, case: EvalCase, run_index: int, fingerprint: str) -> CacheEntry | None:
        path = self._path(case, run_index, fingerprint)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("format") != CACHE_FORMAT:
                return None
            return _from_json(raw)
        except (OSError, ValueError, KeyError, TypeError):
            return None  # missing or corrupt: a miss, never an error

    def put(self, case: EvalCase, run_index: int, fingerprint: str, entry: CacheEntry) -> None:
        path = self._path(case, run_index, fingerprint)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_to_json(entry), ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
