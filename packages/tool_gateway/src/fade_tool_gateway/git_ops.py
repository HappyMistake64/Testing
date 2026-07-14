"""Git operations via subprocess (tool gateway only)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fade_tool_gateway.runner import CommandResult, run_command


@dataclass(frozen=True, slots=True)
class GitWorktreeResult:
    worktree_path: Path
    base_revision: str | None
    stderr: str


def git_rev_parse(repo_path: Path) -> str | None:
    result = run_command(["git", "-C", str(repo_path), "rev-parse", "HEAD"], cwd=str(repo_path))
    if result.exit_code == 0:
        return result.stdout.strip()
    return None


def git_worktree_add(
    repo_path: Path,
    worktree_path: Path,
    branch: str,
) -> GitWorktreeResult:
    result = run_command(
        [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "add",
            "-B",
            branch,
            str(worktree_path),
        ],
        cwd=str(repo_path),
    )
    revision = git_rev_parse(worktree_path) if result.exit_code == 0 else None
    return GitWorktreeResult(
        worktree_path=worktree_path,
        base_revision=revision or git_rev_parse(repo_path),
        stderr=result.stderr,
    )


def git_worktree_remove(repo_path: Path, worktree_path: Path) -> CommandResult:
    return run_command(
        ["git", "-C", str(repo_path), "worktree", "remove", "--force", str(worktree_path)],
        cwd=str(repo_path),
    )
