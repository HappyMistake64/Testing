"""Project analysis orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from fade_domain.project_profile import SymbolEntry

from fade_project_analysis.ignore_engine import IgnoreEngine
from fade_project_analysis.python_parser import parse_python_file
from fade_project_analysis.typescript_parser import parse_typescript_file

_MANIFEST_FILES = frozenset({
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "tsconfig.json",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
})

_FRAMEWORK_HINTS: dict[str, list[str]] = {
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "react": ["react"],
    "vite": ["vite"],
    "next": ["next"],
    "vue": ["vue"],
    "express": ["express"],
}

_PYTHON_EXTS = frozenset({".py"})
_TS_EXTS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Raw analysis output before persistence."""

    languages: list[str]
    frameworks: list[str]
    manifests: list[str]
    commands: dict[str, list[str]]
    architecture_summary: str
    risk_flags: list[str]
    symbols: list[SymbolEntry] = field(default_factory=list)
    revision: str | None = None


def analyze_project(project_path: Path, *, revision: str | None = None) -> AnalysisResult:
    """Run filesystem-based project analysis."""
    engine = IgnoreEngine()
    files = engine.walk_files(project_path)

    languages: set[str] = set()
    manifests: list[str] = []
    symbols: list[SymbolEntry] = []
    risk_flags: list[str] = []

    for file_path in files:
        rel = str(file_path.relative_to(project_path))
        if file_path.name in _MANIFEST_FILES and rel not in manifests:
            manifests.append(rel)

        suffix = file_path.suffix.lower()
        if suffix in _PYTHON_EXTS:
            languages.add("python")
            result = parse_python_file(file_path, project_path)
            if result:
                symbols.extend(result.symbols)
        elif suffix in _TS_EXTS:
            languages.add("typescript")
            result = parse_typescript_file(file_path, project_path)
            if result:
                symbols.extend(result.symbols)

    frameworks = _detect_frameworks(project_path, manifests)
    commands = _discover_commands(project_path, manifests)
    architecture_summary = _build_summary(languages, frameworks, manifests, len(symbols))

    if not manifests:
        risk_flags.append("no_manifest_detected")
    if len(symbols) == 0:
        risk_flags.append("no_symbols_indexed")

    return AnalysisResult(
        languages=sorted(languages),
        frameworks=frameworks,
        manifests=manifests,
        commands=commands,
        architecture_summary=architecture_summary,
        risk_flags=risk_flags,
        symbols=symbols,
        revision=revision,
    )


def _detect_frameworks(project_path: Path, manifests: list[str]) -> list[str]:
    found: set[str] = set()
    for manifest in manifests:
        path = project_path / manifest
        try:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        for framework, hints in _FRAMEWORK_HINTS.items():
            if any(h in text for h in hints):
                found.add(framework)
    return sorted(found)


def _discover_commands(project_path: Path, manifests: list[str]) -> dict[str, list[str]]:
    commands: dict[str, list[str]] = {}
    if "pyproject.toml" in manifests:
        commands["install"] = ["uv sync"]
        commands["test"] = ["pytest"]
        commands["lint"] = ["ruff check ."]
    if "package.json" in manifests:
        pkg = project_path / "package.json"
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if "test" in scripts:
                commands.setdefault("test", []).append("pnpm test")
            if "build" in scripts:
                commands.setdefault("build", []).append("pnpm build")
            if "lint" in scripts:
                commands.setdefault("lint", []).append("pnpm lint")
            commands.setdefault("install", []).append("pnpm install")
        except (OSError, json.JSONDecodeError):
            commands.setdefault("install", []).append("pnpm install")
    return commands


def _build_summary(
    languages: set[str],
    frameworks: list[str],
    manifests: list[str],
    symbol_count: int,
) -> str:
    lang = ", ".join(sorted(languages)) or "unknown"
    fw = ", ".join(frameworks) or "none detected"
    return (
        f"Languages: {lang}. Frameworks: {fw}. "
        f"Manifests: {len(manifests)}. Indexed symbols: {symbol_count}."
    )
