"""Parse unified git diff output into structured file changes."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedDiffFile:
    path: str
    status: str
    additions: int
    deletions: int
    patch: str


_DIFF_FILE_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


def parse_unified_diff(diff_text: str) -> list[ParsedDiffFile]:
    """Split a unified diff into per-file records."""
    if not diff_text.strip():
        return []

    files: list[ParsedDiffFile] = []
    current_path: str | None = None
    current_lines: list[str] = []

    for line in diff_text.splitlines():
        match = _DIFF_FILE_RE.match(line)
        if match:
            if current_path is not None:
                files.append(_finalize_file(current_path, current_lines))
            current_path = match.group(2)
            current_lines = [line]
            continue
        if current_path is not None:
            current_lines.append(line)

    if current_path is not None:
        files.append(_finalize_file(current_path, current_lines))

    return files


def _finalize_file(path: str, lines: list[str]) -> ParsedDiffFile:
    patch = "\n".join(lines)
    if patch and not patch.endswith("\n"):
        patch += "\n"

    additions = 0
    deletions = 0
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    status = "modified"
    if any(line.startswith("new file mode") for line in lines):
        status = "added"
    elif any(line.startswith("deleted file mode") for line in lines):
        status = "deleted"

    return ParsedDiffFile(
        path=path,
        status=status,
        additions=additions,
        deletions=deletions,
        patch=patch,
    )
