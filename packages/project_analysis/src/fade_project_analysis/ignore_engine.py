"""Gitignore-style path filtering for analysis."""

from __future__ import annotations

import fnmatch
from pathlib import Path

_DEFAULT_IGNORE_DIRS = frozenset({
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "coverage",
    ".next",
    ".nuxt",
    "target",
})

_DEFAULT_IGNORE_GLOBS = (
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "uv.lock",
    "poetry.lock",
)


class IgnoreEngine:
    """Filters paths using directory names and glob patterns."""

    def __init__(
        self,
        *,
        ignore_dirs: frozenset[str] | None = None,
        ignore_globs: tuple[str, ...] | None = None,
        extra_patterns: list[str] | None = None,
    ) -> None:
        self._ignore_dirs = ignore_dirs or _DEFAULT_IGNORE_DIRS
        self._ignore_globs = ignore_globs or _DEFAULT_IGNORE_GLOBS
        self._extra_patterns = extra_patterns or []
        self._gitignore_patterns = self._load_gitignore_patterns()

    def _load_gitignore_patterns(self) -> list[str]:
        patterns: list[str] = []
        for pattern in self._extra_patterns:
            patterns.append(pattern)
        return patterns

    def load_gitignore(self, project_root: Path) -> None:
        """Load patterns from .gitignore if present."""
        gitignore = project_root / ".gitignore"
        if not gitignore.is_file():
            return
        try:
            content = gitignore.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            self._gitignore_patterns.append(line)

    def should_ignore_dir(self, name: str) -> bool:
        return name in self._ignore_dirs or name.startswith(".")

    def should_ignore_file(self, rel_path: str) -> bool:
        filename = Path(rel_path).name
        for pattern in self._ignore_globs:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True
        for pattern in self._gitignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(filename, pattern):
                return True
            if pattern.endswith("/") and rel_path.startswith(pattern):
                return True
        return False

    def walk_files(self, project_root: Path) -> list[Path]:
        """Return analyzable files under project root."""
        self.load_gitignore(project_root)
        files: list[Path] = []
        stack = [project_root]
        while stack:
            current = stack.pop()
            try:
                entries = list(current.iterdir())
            except OSError:
                continue
            dirs: list[Path] = []
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    if not self.should_ignore_dir(entry.name):
                        dirs.append(entry)
                elif entry.is_file():
                    rel = str(entry.relative_to(project_root))
                    if not self.should_ignore_file(rel):
                        files.append(entry)
            stack.extend(reversed(dirs))
        return files
