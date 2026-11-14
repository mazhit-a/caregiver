from pathlib import Path

from tests.architecture.test_plan_purity import STDLIB, _imported_roots

DOMAIN = Path(__file__).resolve().parents[2] / "app" / "domain"


def test_roleplay_and_safety_import_only_stdlib_and_domain() -> None:
    for pkg in ("roleplay", "safety"):
        files = sorted((DOMAIN / pkg).glob("*.py"))
        assert files
        for file in files:
            for module in _imported_roots(file):
                ok = module.split(".")[0] in STDLIB or module.startswith("app.domain")
                assert ok, f"{file} imports {module}"
