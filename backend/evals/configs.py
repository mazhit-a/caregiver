"""Named candidate configurations (search plan, ai.md section 4). Stage 3 (harness shape) needs
harnesses that arrive in increment 22; here only single-call candidates exist."""

from evals.client import CoachConfig

# Stage 2: model x effort (prompt version is chosen with --prompt-version).
_STAGE2: tuple[tuple[str, str, str, dict[str, str] | None], ...] = (
    ("haiku-nothink", "claude-haiku-5-5", "low", {"type": "disabled"}),
    ("haiku-low", "claude-haiku-5-5", "low", None),
    ("sonnet-low", "claude-sonnet-5-5", "low", None),
    ("sonnet-medium", "claude-sonnet-5-5", "medium", None),
    ("opus-low", "claude-opus-5-5", "low", None),
    ("opus-medium", "claude-opus-5-5", "medium", None),
)
STAGES: dict[str, tuple[str, ...]] = {
    "prompt": ("opus-low",),
    "model-effort": tuple(n for n, *_ in _STAGE2),
}


def candidate(name: str, prompt_version: str) -> CoachConfig:
    for n, model, effort, thinking in _STAGE2:
        if n == name:
            return CoachConfig(
                name=f"{n}-v{prompt_version}",
                model=model,
                effort=effort,
                prompt_version=prompt_version,
                thinking=thinking,
            )
    raise KeyError(name)


def candidate_names() -> tuple[str, ...]:
    return tuple(n for n, *_ in _STAGE2)
