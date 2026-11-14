"""The CLI's real-model path, driven only by a fake SDK client (no key, no network)."""

import json
from pathlib import Path

import pytest

from app.infrastructure.config import Settings
from evals.dataset import Split, load_split
from evals.run import main
from tests.evals.conftest import CONTENT_DIR
from tests.evals.test_runner import FakeSdkClient

BASE = ["--set", "test", "--runs", "2"]
CALLS = len(load_split(Split.TEST)) * 2  # test-split cases x 2 runs


def _settings() -> Settings:
    return Settings(anthropic_api_key="", content_dir=CONTENT_DIR)


def _args(tmp_path: Path, *extra: str) -> list[str]:
    return [
        *BASE,
        "--cache-dir",
        str(tmp_path / "cache"),
        "--report-dir",
        str(tmp_path / "rep"),
        *extra,
    ]


def _run(argv: list[str], client: FakeSdkClient | None, **kw: object) -> int:
    return main(
        argv,
        settings=_settings(),
        client_factory=lambda _s: client,
        today=__import__("datetime").date(2026, 11, 14),
        **kw,  # type: ignore[arg-type]
    )


def test_runner_refuses_real_calls_without_confirmation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client = FakeSdkClient()
    prompts: list[str] = []

    def say_no(prompt: str) -> str:
        prompts.append(prompt)
        return "n"

    assert _run(_args(tmp_path), client, input_fn=say_no, interactive=True) == 2
    assert len(prompts) == 1 and f"{CALLS} real model calls" in prompts[0]
    assert client.requests == []  # the fake model was never called
    assert not (tmp_path / "rep").exists()
    captured = capsys.readouterr()
    assert "Cost estimate" in captured.out and "Refused" in captured.err


def test_non_interactive_yes_needs_a_cap_the_estimate_is_below(tmp_path: Path) -> None:
    client = FakeSdkClient()
    assert _run(_args(tmp_path, "--yes"), client, interactive=False) == 2
    assert (
        _run(_args(tmp_path, "--yes", "--max-cost-usd", "0.0000001"), client, interactive=False)
        == 2
    )
    assert _run(_args(tmp_path), client, interactive=False) == 2  # cannot prompt
    assert client.requests == []


def test_dry_run_prints_estimate_and_makes_no_calls(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client = FakeSdkClient()
    called: list[object] = []

    def factory(_s: Settings) -> FakeSdkClient:
        called.append(1)
        return client

    code = main(_args(tmp_path, "--dry-run"), settings=_settings(), client_factory=factory)
    out = capsys.readouterr().out
    assert code == 0 and client.requests == [] and called == []  # not even a client is built
    assert f"TOTAL {CALLS} calls" in out and "Dry run" in out


def test_missing_key_is_refused_after_the_estimate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(_args(tmp_path, "--yes", "--max-cost-usd", "5"), None, interactive=False) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_confirmed_run_writes_reports_and_a_rerun_calls_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client = FakeSdkClient()
    argv = _args(tmp_path, "--yes", "--max-cost-usd", "5", "--stage", "smoke")
    # The fake model flags nothing, so the safety gate fails: no winner, exit code 1.
    assert _run(argv, client, interactive=False) == 1
    assert len(client.requests) == CALLS
    report = json.loads((tmp_path / "rep" / "2026-11-14-smoke.json").read_text(encoding="utf-8"))
    assert (tmp_path / "rep" / "2026-11-14-smoke.md").is_file()
    assert report["configs"][0]["metrics"]["safety"]["needed"] > 0
    assert report["selection"]["winner"] is None
    assert "safety_recall" in str(report["selection"]["excluded"])
    capsys.readouterr()
    # Same arguments again: everything is cached, so no calls and no confirmation needed.
    assert _run(argv, client, interactive=False) == 1
    assert len(client.requests) == CALLS
    assert "TOTAL 0 calls" in capsys.readouterr().out


def test_batch_flag_is_a_refused_todo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(_args(tmp_path, "--batch"), FakeSdkClient()) == 2
    assert "not implemented" in capsys.readouterr().err
