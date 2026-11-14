"""Stage presets of the search plan (prompt, model-effort, harness)."""

import pytest

from evals.configs import STAGES, candidate


def test_prompt_stage_compares_v1_and_v2_on_opus_low() -> None:
    configs = [candidate(n, "9") for n in STAGES["prompt"]]  # "9" must be ignored: names pin it
    assert [(c.model, c.effort, c.prompt_version, c.harness) for c in configs] == [
        ("claude-opus-5-5", "low", "1", "single_call"),
        ("claude-opus-5-5", "low", "2", "single_call"),
    ]
    assert len({c.name for c in configs}) == 2


def test_harness_stage_compares_single_call_and_parallel_split() -> None:
    configs = [candidate(n, "2") for n in STAGES["harness"]]
    assert [c.harness for c in configs] == ["single_call", "parallel_split"]
    assert {(c.model, c.effort, c.prompt_version) for c in configs} == {
        ("claude-opus-5-5", "low", "2")
    }
    assert len({c.name for c in configs}) == 2


def test_candidate_name_without_suffix_keeps_existing_behaviour() -> None:
    c = candidate("sonnet-low", "1")
    assert (c.name, c.harness, c.prompt_version) == ("sonnet-low-v1", "single_call", "1")


@pytest.mark.parametrize("name", ["nope", "opus-low+chained"])
def test_unknown_candidate_or_harness_is_rejected(name: str) -> None:
    with pytest.raises(KeyError):
        candidate(name, "1")
