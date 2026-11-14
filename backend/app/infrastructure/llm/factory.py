"""Builds the configured `Coach` (harness, model, effort and prompt version come from Settings)."""

from anthropic import AsyncAnthropic

from app.application.ports import Coach
from app.infrastructure.config import Settings
from app.infrastructure.llm.anthropic_coach import AnthropicCoach
from app.infrastructure.llm.prompt import load_prompt


class UnknownHarnessError(ValueError):
    """COACH_HARNESS names a harness that is not implemented: startup must fail."""


def build_coach(settings: Settings) -> Coach:
    """Raises `PromptLoadError` / `UnknownHarnessError` so a bad config stops the app at startup.

    Without an API key the adapter is still built; every turn then raises `CoachUnavailable`.
    """
    if settings.coach_harness != "single_call":
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
    return AnthropicCoach(
        client,
        prompt=prompt,
        model=settings.coach_model,
        effort=settings.coach_effort,
        timeout_seconds=settings.llm_timeout_seconds,
    )
