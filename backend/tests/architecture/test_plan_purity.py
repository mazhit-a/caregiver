import ast
import sys
from pathlib import Path

PLAN_DIR = Path(__file__).resolve().parents[2] / "app" / "domain" / "plan"
STDLIB = set(sys.stdlib_module_names)


def _imported_roots(path: Path) -> list[str]:
    roots: list[str] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            roots.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.append(node.module)
    return roots


def test_plan_module_imports_only_stdlib_and_domain() -> None:
    files = sorted(PLAN_DIR.glob("*.py"))
    assert {f.name for f in files} >= {"builder.py", "entities.py"}
    for file in files:
        for module in _imported_roots(file):
            root = module.split(".")[0]
            allowed = root in STDLIB or module == "app.domain" or module.startswith("app.domain.")
            assert allowed, f"{file.name} imports {module}"
