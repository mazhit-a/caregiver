"""Cost estimate for judge calls, reusing the increment-20 estimate and confirmation gate.

A real judge run (calibration or grading a configuration) estimates calls x tokens x price with
the same `estimate_run` / `confirm_run` as the coach runs, so `--max-cost-usd` means the same.
The estimate is the worst case (no cache hits); output tokens use the per-effort allowance table.
"""

from collections.abc import Sequence
from typing import Final

from evals.client import CoachConfig
from evals.cost import (
    CHARS_PER_TOKEN,
    DEFAULT_OUTPUT_TOKENS,
    OUTPUT_TOKENS_BY_EFFORT,
    CostEstimate,
    TokenEstimate,
    estimate_run,
)
from evals.graders.judge import JudgeItem, JudgePrompt, build_judge_message
from evals.metrics import PriceTable

JUDGE_CONFIG_NAME: Final = "judge"


def estimate_judge_run(
    items: Sequence[JudgeItem],
    prompt: JudgePrompt,
    *,
    model: str,
    effort: str,
    prices: PriceTable,
    calls: int | None = None,
) -> CostEstimate:
    """`calls` defaults to one per item."""
    prefix = int(len(prompt.system) / CHARS_PER_TOKEN)
    user = [len(build_judge_message(i)) for i in items]
    mean_user = int(sum(user) / len(user) / CHARS_PER_TOKEN) if user else 0
    tokens = TokenEstimate(
        input_tokens=prefix + mean_user,
        output_tokens=OUTPUT_TOKENS_BY_EFFORT.get(effort, DEFAULT_OUTPUT_TOKENS),
        cacheable_input_tokens=prefix,
    )
    config = CoachConfig(
        name=JUDGE_CONFIG_NAME, model=model, effort=effort, prompt_version=prompt.version
    )
    return estimate_run([(config, len(items) if calls is None else calls, tokens)], prices)
