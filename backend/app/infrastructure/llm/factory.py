"""Builds the configured `Coach` (harness, models, effort and prompt version come from Settings).

`HARNESSES` is the registry keyed by `COACH_HARNESS`; every entry implements the `Coach` port.
"""

from collections.abc import Callable
from typing import Final

from anthropic import AsyncAnthropic

from app.application.ports import Coach
from app.infrastructure.config import Settings
from app.infrastructure.llm import anthropic_coach, parallel_split
from app.infrastructure.llm.anthropic_coach import AnthropicCoach, CallMetrics
from app.infrastructure.llm.parallel_split import ParallelSplitCoach
from app.infrastructure.llm.prompt import PromptSpec, load_prompt

HARNESSES: Final = (anthropic_coach.HARNESS_ID, parallel_split.HARNESS_ID)


class UnknownHarnessError(ValueError):
    """COACH_HARNESS names a harness that is not implemented: startup must fail."""


def make_coach(
    harness: str,
    client: AsyncAnthropic | None,
    *,
    prompt: PromptSpec,
    model: str,
    parent_model: str | None,
    effort: str,
    timeout_seconds: float,
    thinking: dict[str, str] | None = None,
    metrics_sink: Callable[[CallMetrics], None] | None = None,
) -> Coach:
    """The registry: one place that maps a harness id to its implementation (also used by evals).

    `parent_model` only applies to `parallel_split`; `None` means the same model as `model`.
    """
    if harness == anthropic_coach.HARNESS_ID:
        return AnthropicCoach(
            client,
            prompt=prompt,
            model=model,
            effort=effort,
            timeout_seconds=timeout_seconds,
            thinking=thinking,
            metrics_sink=metrics_sink,
        )
    if harness == parallel_split.HARNESS_ID:
        return ParallelSplitCoach(
            client,
            prompt=prompt,
            model=model,
            parent_model=parent_model,
            effort=effort,
            timeout_seconds=timeout_seconds,
            thinking=thinking,
            metrics_sink=metrics_sink,
        )
    raise UnknownHarnessError(f"Unknown COACH_HARNESS: {harness!r}")


def build_coach(settings: Settings) -> Coach:
    """Raises `PromptLoadError` / `UnknownHarnessError` so a bad config stops the app at startup.

    Without an API key the adapter is still built; every turn then raises `CoachUnavailable`.
    """
    if settings.coach_harness not in HARNESSES:
        raise UnknownHarnessError(f"Unknown COACH_HARNESS: {settings.coach_harness!r}")
    prompt = load_prompt(settings.content_dir, settings.coach_prompt_version)
    client = (
        AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            max_retries=0,
            timeout=settings.llm_timeout_seconds,
        )
        if settings.anthropic_api_key
        else None
    )
    return make_coach(
        settings.coach_harness,
        client,
        prompt=prompt,
        model=settings.coach_model,
        parent_model=settings.coach_parent_model or None,
        effort=settings.coach_effort,
        timeout_seconds=settings.llm_timeout_seconds,
        thinking=settings.coach_thinking_param,
    )
