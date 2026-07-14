"""Read-only Git metadata from filesystem (no subprocess)."""

from __future__ import annotations

from pathlib import Path

from fade_domain.project import GitMetadata

_MANIFEST_NAMES = frozenset({
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pubspec.yaml",
    "Makefile",
    "docker-compose.yml",
    "docker-compose.yaml",
})

_SENSITIVE_PATTERNS = (
    ".env",
    ".env.",
    "secrets",
    "secret",
    "credentials",
    "id_rsa",
    "id_ed25519",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    "token",
    "password",
)

_IGNORE_DIRS = frozenset({
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
})


def read_git_metadata(project_path: Path) -> GitMetadata:
    """Inspect Git metadata without invoking git CLI."""
    git_dir = project_path / ".git"
    if not git_dir.exists():
        return GitMetadata(is_git_repo=False)

    head_path = git_dir / "HEAD"
    if not head_path.is_file():
        return GitMetadata(is_git_repo=True, branch=None, revision=None, dirty=None)

    head_content = head_path.read_text(encoding="utf-8").strip()
    branch: str | None = None
    revision: str | None = None

    if head_content.startswith("ref: "):
        ref = head_content[5:]
        branch = ref.removeprefix("refs/heads/")
        ref_path = git_dir / ref
        if ref_path.is_file():
            revision = ref_path.read_text(encoding="utf-8").strip()[:12]
    else:
        revision = head_content[:12]

    dirty = _detect_dirty(git_dir)
    return GitMetadata(
        is_git_repo=True,
        branch=branch,
        revision=revision,
        dirty=dirty,
    )


def _detect_dirty(git_dir: Path) -> bool | None:
    """Best-effort dirty detection without git CLI."""
    if (git_dir / "MERGE_HEAD").exists():
        return True
    if (git_dir / "CHERRY_PICK_HEAD").exists():
        return True
    if (git_dir / "rebase-merge").exists():
        return True
    return None


def scan_inventory(
    project_path: Path,
    *,
    max_files: int = 50_000,
    max_bytes: int = 2_000_000_000,
) -> tuple[int, int, list[str], list[str]]:
    """Scan project directory for file count, size, manifests, sensitive names."""
    file_count = 0
    total_bytes = 0
    manifests: list[str] = []
    sensitive: list[str] = []

    for root, dirs, files in _walk_safe(project_path):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS and not d.startswith(".git")]

        for filename in files:
            file_path = root / filename
            try:
                stat = file_path.stat()
            except OSError:
                continue

            file_count += 1
            total_bytes += stat.st_size

            rel = str(file_path.relative_to(project_path))
            if filename in _MANIFEST_NAMES and rel not in manifests:
                manifests.append(rel)

            lower = rel.lower()
            if any(p in lower for p in _SENSITIVE_PATTERNS):
                sensitive.append(rel)

            if file_count > max_files:
                return file_count, total_bytes, manifests, sensitive

    return file_count, total_bytes, manifests, sensitive


def _walk_safe(root: Path):
    """Walk directory tree without following symlinks."""
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        dirs: list[Path] = []
        files: list[Path] = []
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in _IGNORE_DIRS:
                    dirs.append(entry)
            elif entry.is_file():
                files.append(entry)
        yield current, dirs, [f.name for f in files]
        stack.extend(reversed(dirs))
