"""Create test Git repository fixtures."""

from __future__ import annotations

from pathlib import Path


def create_git_repo(path: Path | str, *, branch: str = "main", with_manifest: bool = True) -> Path:
    """Create a minimal Git repo structure for testing (no git CLI)."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    git_dir = path / ".git"
    git_dir.mkdir()
    refs_heads = git_dir / "refs" / "heads"
    refs_heads.mkdir(parents=True)

    commit_sha = "a" * 40
    (refs_heads / branch).write_text(f"{commit_sha}\n", encoding="utf-8")
    (git_dir / "HEAD").write_text(f"ref: refs/heads/{branch}\n", encoding="utf-8")

    if with_manifest:
        (path / "pyproject.toml").write_text(
            '[project]\nname = "fixture"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
        (path / "README.md").write_text("# Fixture Project\n", encoding="utf-8")

    return path


def create_non_git_project(path: Path | str) -> Path:
    """Create a plain directory without Git."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text("# No Git\n", encoding="utf-8")
    return path
