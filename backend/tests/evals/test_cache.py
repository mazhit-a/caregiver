"""Result cache: hits skip the model; any change in what is asked is a miss."""

import shutil
from pathlib import Path

import pytest

from app.application.roleplay.dto import CoachInput
from app.domain.roleplay.verdict import CoachVerdict
from evals.cache import CacheEntry, ResultCache, config_fingerprint, fingerprint_parts
from evals.client import CoachConfig
from evals.runner import EvalContext, run_measured
from tests.evals.conftest import CONTENT_DIR, make_call, make_case, make_verdict

CONFIG = CoachConfig(name="c", model="claude-opus-5-5", effort="low", prompt_version="1")


class CountingCoach:
    def __init__(self, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    async def turn(self, coach_input: CoachInput) -> CoachVerdict:
        self.calls += 1
        if self.fail:
            from app.application.ports import CoachUnavailable

            raise CoachUnavailable("x")
        return make_verdict()


async def test_cache_hit_skips_model_call_and_changed_prompt_version_misses(
    ctx: EvalContext, tmp_path: Path
) -> None:
    content = tmp_path / "content"
    shutil.copytree(CONTENT_DIR / "prompts", content / "prompts")
    shutil.copy(
        content / "prompts" / "roleplay-turn.v1.md", content / "prompts" / "roleplay-turn.v2.md"
    )
    cache = ResultCache(tmp_path / "cache")
    cases = [make_case(id="a"), make_case(id="b")]
    fp1 = config_fingerprint(CONFIG, content)

    first = CountingCoach()
    await run_measured(first, cases, ctx, runs=2, cache=cache, fingerprint=fp1)
    assert first.calls == 4

    second = CountingCoach()
    again = await run_measured(second, cases, ctx, runs=2, cache=cache, fingerprint=fp1)
    assert second.calls == 0 and all(m.cached for m in again)
    assert all(m.result.passed for m in again)  # graders are re-applied on the cached verdict

    # A new prompt version (even with an identical file body) is a miss.
    v2 = CoachConfig(name="c", model=CONFIG.model, effort="low", prompt_version="2")
    third = CountingCoach()
    await run_measured(
        third, cases, ctx, runs=2, cache=cache, fingerprint=config_fingerprint(v2, content)
    )
    assert third.calls == 4

    # Only the new run index / new case calls the model.
    fourth = CountingCoach()
    await run_measured(
        fourth, [*cases, make_case(id="c")], ctx, runs=3, cache=cache, fingerprint=fp1
    )
    assert fourth.calls == 3 * 3 - 4


def test_fingerprint_changes_with_each_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = tmp_path / "content"
    shutil.copytree(CONTENT_DIR / "prompts", content / "prompts")
    base = config_fingerprint(CONFIG, content)
    assert base == config_fingerprint(CONFIG, content)  # stable
    for changed in (
        CoachConfig(name="c", model="claude-sonnet-5-5", effort="low", prompt_version="1"),
        CoachConfig(name="c", model=CONFIG.model, effort="medium", prompt_version="1"),
        CoachConfig(
            name="c",
            model=CONFIG.model,
            effort="low",
            prompt_version="1",
            thinking={"type": "disabled"},
        ),
    ):
        assert config_fingerprint(changed, content) != base
    # the name is a label, not part of what is asked
    assert config_fingerprint(CoachConfig("other", CONFIG.model, "low", "1"), content) == base
    # the prompt FILE hash
    prompt = content / "prompts" / "roleplay-turn.v1.md"
    prompt.write_text(prompt.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert config_fingerprint(CONFIG, content) != base
    # the adapter's INPUT_FORMAT_NOTE
    after_file = config_fingerprint(CONFIG, content)
    monkeypatch.setattr("evals.cache.INPUT_FORMAT_NOTE", "another note")
    assert config_fingerprint(CONFIG, content) != after_file
    parts = fingerprint_parts(CONFIG, content)
    assert {"promptFileSha256", "inputFormatNoteSha256", "promptVersion", "model"} <= set(parts)


async def test_edited_case_and_failed_calls_are_not_served_from_cache(
    ctx: EvalContext, tmp_path: Path
) -> None:
    cache = ResultCache(tmp_path)
    await run_measured(CountingCoach(fail=True), [make_case()], ctx, cache=cache, fingerprint="fp")
    coach = CountingCoach()
    await run_measured(coach, [make_case()], ctx, cache=cache, fingerprint="fp")
    assert coach.calls == 1  # the failure was not cached
    edited = CountingCoach()
    await run_measured(
        edited,
        [make_case(caregiverReply="Different words now.")],
        ctx,
        cache=cache,
        fingerprint="fp",
    )
    assert edited.calls == 1  # same id, new content: a miss
    hit = CountingCoach()
    await run_measured(hit, [make_case()], ctx, cache=cache, fingerprint="fp")
    assert hit.calls == 0


def test_cache_entry_round_trip_and_corrupt_file_is_a_miss(tmp_path: Path) -> None:
    cache = ResultCache(tmp_path)
    case = make_case()
    entry = CacheEntry(make_verdict(flags=("medical",)), 812.5, make_call(cache_read=5))
    cache.put(case, 0, "fp", entry)
    assert cache.get(case, 0, "fp") == entry
    assert cache.get(case, 1, "fp") is None
    (next(tmp_path.rglob("*.json"))).write_text("{not json")
    assert cache.get(case, 0, "fp") is None
