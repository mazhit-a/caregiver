"""How the runner gets a `Coach` for a configuration, and the model-client seam.

The eval never re-implements the prompt: it builds the production `AnthropicCoach` (same system
prompt loading, request building, parsing and failure mapping) with its own model / effort /
thinking / prompt version. `ModelClient` is the seam: the real `AsyncAnthropic` in a manual run, a
fake SDK-shaped object in tests, so the real adapter code runs offline.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast

from anthropic import AsyncAnthropic

from app.application.ports import Coach
from app.infrastructure.config import Settings
from app.infrastructure.llm.anthropic_coach import HARNESS_ID, AnthropicCoach, CallMetrics
from app.infrastructure.llm.prompt import load_prompt


class ModelClient(Protocol):
    """The slice of the Anthropic SDK client that `AnthropicCoach` uses."""

    def with_options(self, *, max_retries: int, timeout: float) -> Any: ...


@dataclass(frozen=True)
class CoachConfig:
    """One harness configuration under evaluation."""

    name: str
    model: str
    effort: str
    prompt_version: str
    harness: str = HARNESS_ID
    thinking: dict[str, str] | None = None


class UnknownHarness(ValueError):
    """The config names a harness this runner cannot build yet."""


def production_config(settings: Settings) -> CoachConfig:
    """What the app runs with today (Settings defaults)."""
    return CoachConfig(
        name="production",
        model=settings.coach_model,
        effort=settings.coach_effort,
        prompt_version=settings.coach_prompt_version,
        harness=settings.coach_harness,
    )


def real_client(settings: Settings) -> ModelClient | None:
    """The real SDK client, or None without a key (every turn then fails as unavailable)."""
    if not settings.anthropic_api_key:
        return None
    return cast(
        ModelClient,
        AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            max_retries=0,
            timeout=settings.llm_timeout_seconds,
        ),
    )


def build_eval_coach(
    config: CoachConfig,
    settings: Settings,
    client: ModelClient | None,
    *,
    metrics_sink: Callable[[CallMetrics], None] | None = None,
) -> Coach:
    """The production adapter for `config`. Raises `UnknownHarness` / `PromptLoadError`."""
    if config.harness != HARNESS_ID:
        raise UnknownHarness(f"Harness {config.harness!r} is not implemented")
    return AnthropicCoach(
        cast(AsyncAnthropic | None, client),
        prompt=load_prompt(settings.content_dir, config.prompt_version),
        model=config.model,
        effort=config.effort,
        timeout_seconds=settings.llm_timeout_seconds,
        thinking=config.thinking,
        metrics_sink=metrics_sink,
    )
