"""Architecture boundary tests for subprocess usage."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = [
    ROOT / "packages" / "infrastructure" / "src",
    ROOT / "packages" / "application" / "src",
    ROOT / "apps" / "api",
    ROOT / "packages" / "verification" / "src",
    ROOT / "packages" / "repair_loop" / "src",
    ROOT / "packages" / "guardian" / "src",
    ROOT / "packages" / "patch_engine" / "src",
]
ALLOWED_SUBPROCESS = ROOT / "packages" / "tool_gateway" / "src" / "fade_tool_gateway" / "runner.py"


def _imports_subprocess(file_path: Path) -> bool:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    return True
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            return True
    return False


class TestSubprocessBoundary:
    def test_subprocess_only_in_tool_gateway_runner(self) -> None:
        violations: list[str] = []
        for base in SCAN_DIRS:
            if not base.exists():
                continue
            for py_file in base.rglob("*.py"):
                if _imports_subprocess(py_file):
                    violations.append(str(py_file.relative_to(ROOT)))

        tool_gateway_dir = ROOT / "packages" / "tool_gateway" / "src" / "fade_tool_gateway"
        for py_file in tool_gateway_dir.rglob("*.py"):
            if py_file.name != "runner.py" and _imports_subprocess(py_file):
                violations.append(str(py_file.relative_to(ROOT)))

        assert violations == [], f"subprocess used outside tool_gateway/runner.py: {violations}"

    def test_runner_uses_subprocess(self) -> None:
        assert ALLOWED_SUBPROCESS.exists()
        assert _imports_subprocess(ALLOWED_SUBPROCESS)
