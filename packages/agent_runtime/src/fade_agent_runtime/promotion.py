"""Promote approved workspace changes back to the registered project source."""

from __future__ import annotations

import shutil
from pathlib import Path

from fade_tool_gateway.gateway import ToolGateway

from fade_agent_runtime.diff import parse_unified_diff


class PromotionError(Exception):
    """Raised when workspace changes cannot be promoted."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def promote_workspace_to_source(
    *,
    workspace_path: Path,
    source_path: Path,
    diff_text: str,
    file_paths: list[str] | None = None,
) -> list[str]:
    """Copy changed files from workspace into the original project tree."""
    if not source_path.is_dir():
        msg = f"Source path does not exist: {source_path}"
        raise PromotionError("SOURCE_NOT_FOUND", msg)

    paths = list(file_paths or [])
    if not paths:
        files = parse_unified_diff(diff_text)
        if not files:
            msg = "No diff files to promote"
            raise PromotionError("EMPTY_DIFF", msg)
        paths = [file.path for file in files if file.status != "deleted"]

    if not paths:
        msg = "No diff files to promote"
        raise PromotionError("EMPTY_DIFF", msg)

    promoted: list[str] = []
    for rel_path in paths:
        src_file = workspace_path / rel_path
        if not src_file.is_file():
            continue
        dest_file = source_path / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)
        promoted.append(rel_path)
    return promoted


def workspace_diff_text(workspace_path: Path) -> str:
    gateway = ToolGateway.for_workspace(workspace_path)
    return gateway.git_diff().diff
