"""Architecture boundary tests."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

DOMAIN_SRC = Path(__file__).resolve().parents[2] / "packages" / "domain" / "src" / "fade_domain"

FORBIDDEN_IMPORTS = frozenset({
    "fastapi",
    "sqlalchemy",
    "pydantic_settings",
    "structlog",
    "react",
    "httpx",
    "uvicorn",
})


def _collect_imports(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


class TestDomainBoundaries:
    def test_domain_does_not_import_infrastructure(self) -> None:
        violations: list[str] = []
        for py_file in DOMAIN_SRC.rglob("*.py"):
            found = _collect_imports(py_file) & FORBIDDEN_IMPORTS
            if found:
                violations.append(f"{py_file.name}: {sorted(found)}")
        assert violations == [], f"Domain boundary violations: {violations}"

    def test_domain_package_importable(self) -> None:
        spec = importlib.util.find_spec("fade_domain")
        assert spec is not None
