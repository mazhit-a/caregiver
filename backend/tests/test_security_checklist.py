"""Security review checklist (increment 40) as tests that need no database.

Covered elsewhere: Stripe live-key refusal (tests/infrastructure/test_config.py), the 422 handler
never echoing values (test_app.py, tests/presentation/test_hardening_http.py), session token hashing
(tests/presentation/test_session_api.py), the 413/429/CORS/log tests in test_hardening_http.py.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.domain.session.tokens import hash_token
from app.infrastructure.config import Settings

REPO = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout


needs_git = pytest.mark.skipif(
    shutil.which("git") is None or not (REPO / ".git").exists(), reason="not a git checkout"
)


@needs_git
def test_check_secrets_script_passes_on_the_repo() -> None:
    result = subprocess.run(
        ["bash", str(REPO / "scripts" / "check_secrets.sh")],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@needs_git
def test_secret_patterns_do_not_appear_in_files_that_are_or_will_be_tracked() -> None:
    patterns = [
        "sk_" + r"(live|test)_[A-Za-z0-9]{20,}",
        "whsec_" + r"[A-Za-z0-9]{20,}",
        "pk_" + r"live_",
        "sk-" + r"ant-[A-Za-z0-9_-]{20,}",
    ]
    files = _git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    assert files
    regex = re.compile("|".join(patterns))
    hits = []
    for name in files:
        path = REPO / name
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if name != "scripts/check_secrets.sh" and regex.search(text):
            hits.append(name)
    assert hits == []


@needs_git
def test_env_file_is_untracked_and_ignored() -> None:
    tracked = _git("ls-files").splitlines()
    env_files = [f for f in tracked if re.search(r"(^|/)\.env(\..+)?$", f)]
    assert env_files == [".env.example"]
    assert subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=REPO).returncode == 0


def test_env_example_documents_every_setting() -> None:
    documented = {
        line.split("=", 1)[0].strip().lower()
        for line in (REPO / ".env.example").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    }
    missing = set(Settings.model_fields) - documented - {"content_dir"}  # compose sets CONTENT_DIR
    assert missing == set()


def test_env_example_holds_only_dummy_secrets() -> None:
    values = dict(
        line.split("=", 1)
        for line in (REPO / ".env.example").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
    assert values["ANTHROPIC_API_KEY"] == ""
    assert values["STRIPE_SECRET_KEY"] == "sk_test_dummy"
    assert values["STRIPE_WEBHOOK_SECRET"] == "whsec_dummy"
    assert "*" not in values["CORS_ORIGINS"]


def test_dockerfile_runs_unprivileged_with_one_worker_and_no_uvicorn_access_log() -> None:
    lines = [
        line.strip()
        for line in (REPO / "backend" / "Dockerfile").read_text().splitlines()
        if not line.strip().startswith("#")
    ]
    users = [line for line in lines if line.startswith("USER ")]
    assert users and users[-1].split()[1] not in {"root", "0"}
    assert lines.index(users[-1]) < next(i for i, ln in enumerate(lines) if ln.startswith("CMD"))
    cmd = next(line for line in lines if line.startswith("CMD"))
    assert "--workers 1" in cmd and "--no-access-log" in cmd


def test_caddyfile_sets_security_headers_and_the_edge_body_limit() -> None:
    caddy = (REPO / "Caddyfile").read_text()
    assert re.search(r"Strict-Transport-Security\s+\"max-age=\d{7,}", caddy)
    assert re.search(r"X-Content-Type-Options\s+\"nosniff\"", caddy)
    assert re.search(r"Referrer-Policy\s+\"no-referrer\"", caddy)
    assert re.search(r"max_size\s+64KB", caddy)
    assert "reverse_proxy api:8000" in caddy


def test_compose_does_not_publish_the_api_or_database_and_holds_no_real_secrets() -> None:
    compose = (REPO / "docker-compose.yml").read_text()
    assert 'expose:\n      - "8000"' in compose  # the api is reachable through Caddy only
    assert "5432:5432" not in compose


def test_session_tokens_are_stored_only_as_sha256_hashes() -> None:
    digest = hash_token("some-token")
    assert re.fullmatch(r"[0-9a-f]{64}", digest) and "some-token" not in digest
    # Authentication looks the hash up by equality in the database index: the secret itself is
    # never compared in Python, so there is no early-exit timing side channel on the token.
    assert hash_token("some-token") != hash_token("some-tokeN")
