"""Named candidate configurations (search plan, ai.md section 4).

A candidate name is `<model-effort>[@<prompt version>][+<harness>]`, for example `opus-low@2` or
`opus-low+parallel_split`. Without `@` the version comes from `--prompt-version` (or the settings);
without `+` the harness is `single_call`. Stages: `prompt` (v1 vs v2 on opus-low), `model-effort`,
`harness` (single_call vs parallel_split; run with `--prompt-version 2`, the only version that has
the coach/parent sections, and pass `--config` to use the stage-2 winners instead of opus-low).
"""

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
    "prompt": ("opus-low@1", "opus-low@2"),
    "model-effort": tuple(n for n, *_ in _STAGE2),
    "harness": ("opus-low+single_call", "opus-low+parallel_split"),
}
HARNESS_IDS: tuple[str, ...] = ("single_call", "parallel_split")


def candidate(name: str, prompt_version: str) -> CoachConfig:
    base, _, harness = name.partition("+")
    base, _, pinned = base.partition("@")
    version = pinned or prompt_version
    harness = harness or "single_call"
    if harness not in HARNESS_IDS:
        raise KeyError(name)
    for n, model, effort, thinking in _STAGE2:
        if n == base:
            suffix = "" if harness == "single_call" else f"-{harness}"
            return CoachConfig(
                name=f"{n}-v{version}{suffix}",
                model=model,
                effort=effort,
                prompt_version=version,
                harness=harness,
                thinking=thinking,
            )
    raise KeyError(name)


def candidate_names() -> tuple[str, ...]:
    return tuple(n for n, *_ in _STAGE2)
