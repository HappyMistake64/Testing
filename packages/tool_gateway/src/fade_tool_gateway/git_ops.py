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
    *,
    start_point: str | None = None,
) -> GitWorktreeResult:
    argv = [
        "git",
        "-C",
        str(repo_path),
        "worktree",
        "add",
        "-B",
        branch,
        str(worktree_path),
    ]
    if start_point:
        argv.append(start_point)
    result = run_command(argv, cwd=str(repo_path))
    # A failed add must not report the source revision as a valid base;
    # callers rely on base_revision=None to detect the failure.
    revision = git_rev_parse(worktree_path) if result.exit_code == 0 else None
    return GitWorktreeResult(
        worktree_path=worktree_path,
        base_revision=revision,
        stderr=result.stderr,
    )


def git_worktree_remove(repo_path: Path, worktree_path: Path) -> CommandResult:
    return run_command(
        ["git", "-C", str(repo_path), "worktree", "remove", "--force", str(worktree_path)],
        cwd=str(repo_path),
    )
