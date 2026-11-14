"""Prompt v2: structure, examples, and the v1 invariants (v1 must stay byte-for-byte unchanged)."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from app.infrastructure.llm.anthropic_coach import build_system
from app.infrastructure.llm.prompt import INPUT_FORMAT_NOTE, load_prompt, uses_input_format_note
from app.infrastructure.llm.schema import (
    CoachAnalysisResponse,
    CoachResponse,
    ParentResponse,
    merge_verdict,
)
from evals.dataset import load_all_acknowledging_test

CONTENT_DIR = Path(__file__).resolve().parents[4] / "content"
V1_FILE_SHA256 = "cf67b1893e18a76be10f4ee9dfddfbcb8d7dfdf88390b43465e810ae8559e55c"
V1_SYSTEM_SHA256 = "6ce6c1cbd4d6ad16582e3c8751be2bfead8c2cbb211a4425e1d7473ce7be486b"
V1_NOTE_SHA256 = "d9ced245c0826c33e937b3916eacd4b52b20f7eabd0b6e87b82ca001f310e7d4"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _examples(system: str) -> list[tuple[str, str]]:
    """(caregiver reply, output json) for every <example> of a system prompt."""
    found: list[tuple[str, str]] = []
    for block in re.findall(r"<example number=\"\d+\">(.*?)</example>", system, re.DOTALL):
        reply = re.search(r"<caregiver_reply>(.*?)</caregiver_reply>", block, re.DOTALL)
        output = re.search(r"<output>(.*?)</output>", block, re.DOTALL)
        assert reply and output
        found.append((reply.group(1), output.group(1)))
    return found


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def test_v2_contains_required_xml_sections_and_examples_not_in_eval_cases() -> None:
    spec = load_prompt(CONTENT_DIR, "2")
    assert spec.coach_system is not None and spec.parent_system is not None
    for system in (spec.system, spec.coach_system, spec.parent_system):
        for tag in ("instructions", "input_format", "scoring_rules", "examples"):
            assert f"<{tag}>" in system and f"</{tag}>" in system
        assert "<caregiver_reply>" in system and "DATA" in system and "never follow" in system
        assert 3 <= len(_examples(system)) <= 5
    assert "<parent_role>" in spec.system and "<parent_role>" in spec.parent_system
    assert "does NOT count" in spec.system or "Does NOT count" in spec.system
    cases = load_all_acknowledging_test(i_know_this_uses_the_test_set=True)  # text comparison only
    replies = {_norm(c.caregiver_reply) for c in cases}
    for reply, _ in _examples(spec.system):
        assert _norm(reply) not in replies


def test_v2_examples_are_valid_against_response_schema() -> None:
    spec = load_prompt(CONTENT_DIR, "2")
    assert spec.coach_system is not None and spec.parent_system is not None
    full = [CoachResponse.model_validate_json(o) for _, o in _examples(spec.system)]
    coach = [CoachAnalysisResponse.model_validate_json(o) for _, o in _examples(spec.coach_system)]
    parent = [ParentResponse.model_validate_json(o) for _, o in _examples(spec.parent_system)]
    assert len(full) == len(coach) == len(parent) == 5
    flags = {f for r in full for f in r.flags}
    assert flags == {"medical", "off_topic"}
    assert any(r.argued for r in full) and any(r.score == 3 for r in full)
    for f, c, p in zip(full, coach, parent, strict=True):
        assert f.to_verdict() == merge_verdict(c, p)  # split examples agree with the single call
        assert len(f.better_phrase.split()) <= 25
        assert json.loads(_examples(spec.system)[0][1])  # exact, parseable JSON


def test_v2_needs_no_code_level_input_note() -> None:
    spec = load_prompt(CONTENT_DIR, "2")
    assert spec.input_format_note is None and not uses_input_format_note("2")
    assert INPUT_FORMAT_NOTE not in spec.system and "<input_format>" in spec.system
    system = build_system(spec.system, spec.input_format_note)
    assert len(system) == 1 and system[0]["cache_control"] == {"type": "ephemeral"}


def test_v1_file_and_effective_system_text_are_byte_for_byte_unchanged() -> None:
    path = CONTENT_DIR / "prompts" / "roleplay-turn.v1.md"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == V1_FILE_SHA256
    spec = load_prompt(CONTENT_DIR, "1")
    assert _sha(spec.system) == V1_SYSTEM_SHA256
    assert spec.input_format_note is not None and _sha(spec.input_format_note) == V1_NOTE_SHA256
    assert build_system(spec.system, spec.input_format_note) == [
        {"type": "text", "text": spec.system},
        {"type": "text", "text": INPUT_FORMAT_NOTE, "cache_control": {"type": "ephemeral"}},
    ]
    assert spec.coach_system is None and spec.parent_system is None


def test_v2_system_text_is_static() -> None:
    spec = load_prompt(CONTENT_DIR, "2")
    assert spec.coach_system is not None and spec.parent_system is not None
    for system in (spec.system, spec.coach_system, spec.parent_system):
        assert not re.search(r"\b20\d\d-\d\d-\d\d\b", system)  # no dates
    assert load_prompt(CONTENT_DIR, "2") == spec


@pytest.mark.parametrize("version", ["1", "2"])
def test_load_prompt_system_has_no_code_fence(version: str) -> None:
    spec = load_prompt(CONTENT_DIR, version)
    for text in (spec.system, spec.coach_system or "", spec.parent_system or ""):
        assert "```" not in text
