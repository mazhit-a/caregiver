"""Domain and application never read the clock or generate randomness (CLAUDE.md, Time)."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
SCANNED = [APP / "domain", APP / "application"]

FORBIDDEN_ATTRS = {
    ("datetime", "now"),
    ("datetime", "utcnow"),
    ("date", "today"),
    ("time", "time"),
    ("uuid", "uuid4"),
}
FORBIDDEN_FROM_IMPORTS = {("uuid", "uuid4"), ("time", "time")}


def find_violations(source: str) -> list[str]:
    """Names of forbidden clock/random calls and imports in a module source."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            owner_name = (
                owner.attr if isinstance(owner, ast.Attribute) else getattr(owner, "id", "")
            )
            if (owner_name, node.func.attr) in FORBIDDEN_ATTRS or owner_name == "secrets":
                found.append(f"{owner_name}.{node.func.attr}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "secrets":
                found.append("from secrets import ...")
            found.extend(
                f"from {node.module} import {a.name}"
                for a in node.names
                if (node.module, a.name) in FORBIDDEN_FROM_IMPORTS
            )
    return found


def test_scanner_detects_each_forbidden_call() -> None:
    snippets = [
        "import datetime\ndatetime.datetime.now()",
        "from datetime import datetime\ndatetime.now()",
        "from datetime import datetime\ndatetime.utcnow()",
        "from datetime import date\ndate.today()",
        "import time\ntime.time()",
        "import uuid\nuuid.uuid4()",
        "import secrets\nsecrets.token_urlsafe(8)",
        "from secrets import token_hex",
        "from uuid import uuid4",
    ]
    for snippet in snippets:
        assert find_violations(snippet), snippet
    assert not find_violations("from datetime import datetime\nx = datetime(2026, 1, 1)")


def test_no_clock_or_random_calls_in_domain_or_application() -> None:
    violations: list[str] = []
    for root in SCANNED:
        for path in sorted(root.rglob("*.py")):
            violations += [
                f"{path.relative_to(APP)}: {v}" for v in find_violations(path.read_text())
            ]
    assert violations == []
