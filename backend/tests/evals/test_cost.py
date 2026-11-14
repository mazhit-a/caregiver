"""Cost estimate and confirmation gate (no model, no network)."""

from collections.abc import Callable

import pytest

from evals.client import CoachConfig
from evals.cost import CostEstimate, TokenEstimate, confirm_run, estimate_run, table_token_estimate
from evals.metrics import load_prices
from tests.evals.conftest import CONTENT_DIR, make_case

PRICES = load_prices()
OPUS = CoachConfig(name="opus", model="claude-opus-5-5", effort="low", prompt_version="1")
HAIKU = CoachConfig(name="haiku", model="claude-haiku-5-5", effort="low", prompt_version="1")


def test_cost_estimate_matches_hand_computed_value() -> None:
    # 10 cases x 3 runs = 30 calls per config; 2000 in / 300 out tokens per call, 1500 cacheable.
    tokens = TokenEstimate(input_tokens=2000, output_tokens=300, cacheable_input_tokens=1500)
    est = estimate_run([(OPUS, 30, tokens), (HAIKU, 30, tokens)], PRICES)
    opus = 30 * (2000 * 4.0 + 300 * 20.0) / 1e6  # 30 * 0.014 = 0.42
    haiku = 30 * (2000 * 0.10 + 300 * 0.50) / 1e6  # 30 * 0.00035 = 0.0105
    assert opus == pytest.approx(0.42) and haiku == pytest.approx(0.0105)
    assert est.lines[0].usd == pytest.approx(opus)
    assert est.total_usd == pytest.approx(0.4305)
    assert est.calls == 60
    warm = 30 * (500 * 4.0 + 1500 * 0.20 + 300 * 20.0) / 1e6
    assert est.lines[0].usd_with_cache == pytest.approx(warm)
    assert est.total_usd_with_cache < est.total_usd
    assert est.prices_retrieved_on == "2026-11-14"


def test_table_token_estimate_uses_the_real_prompt_and_message() -> None:
    est = table_token_estimate(OPUS, [make_case()], CONTENT_DIR)
    assert est.cacheable_input_tokens > 500
    assert est.input_tokens > est.cacheable_input_tokens
    assert est.output_tokens == 300  # effort low


def _est(total_calls: int = 30) -> CostEstimate:
    tokens = TokenEstimate(2000, 300)
    return estimate_run([(OPUS, total_calls, tokens)], PRICES)


def _answers(answer: str) -> Callable[[str], str]:
    return lambda _prompt: answer


def test_confirmation_gate_rules() -> None:
    est = _est()  # $0.42
    never = lambda _p: (_ for _ in ()).throw(AssertionError("must not prompt"))  # noqa: E731
    # over the cap is refused even with --yes
    over = confirm_run(est, yes=True, max_cost_usd=0.10, interactive=True, input_fn=never)
    assert not over.approved and "exceeds" in over.reason
    # --yes without a terminal needs a cap
    assert not confirm_run(
        est, yes=True, max_cost_usd=None, interactive=False, input_fn=never
    ).approved
    assert confirm_run(est, yes=True, max_cost_usd=1.0, interactive=False, input_fn=never).approved
    # an interactive --yes is accepted
    assert confirm_run(est, yes=True, max_cost_usd=None, interactive=True, input_fn=never).approved
    # no --yes and no terminal: refused, never prompts
    assert not confirm_run(
        est, yes=False, max_cost_usd=1.0, interactive=False, input_fn=never
    ).approved
    # prompt: only y / yes approve
    for answer, ok in (("y", True), ("YES", True), ("n", False), ("", False), ("sure", False)):
        got = confirm_run(
            est, yes=False, max_cost_usd=None, interactive=True, input_fn=_answers(answer)
        )
        assert got.approved is ok
