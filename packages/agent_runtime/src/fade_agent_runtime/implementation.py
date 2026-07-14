"""Parse and apply structured implementation output."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fade_patch_engine.patch import (
    ApplyPatchResult,
    FileOperation,
    PatchEngine,
    PatchHunk,
    file_hash,
)
from pydantic import ValidationError

from fade_agent_runtime.schemas import ImplementationOutputSchema


class ImplementationParseError(Exception):
    """Raised when model output cannot be parsed."""


def parse_implementation_output(raw: str) -> ImplementationOutputSchema:
    """Parse model JSON output into a validated implementation schema."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
        return ImplementationOutputSchema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        msg = f"Invalid implementation output: {exc}"
        raise ImplementationParseError(msg) from exc


def apply_implementation(
    workspace_root: Path,
    output: ImplementationOutputSchema,
) -> ApplyPatchResult:
    """Apply whole-file changes via the patch engine."""
    engine = PatchEngine(workspace_root)
    hunks: list[PatchHunk] = []

    for change in output.changes:
        resolved = workspace_root / change.path
        current = ""
        if resolved.is_file():
            current = resolved.read_text(encoding="utf-8", errors="replace")
        hunks.append(
            PatchHunk(
                path=change.path,
                base_hash=file_hash(current),
                operations=[
                    FileOperation(
                        path=change.path,
                        old_content=current or None,
                        new_content=change.new_content,
                    ),
                ],
            ),
        )

    return engine.apply_hunks(hunks)


def collect_context_files(
    workspace_root: Path,
    *,
    relative_paths: list[str],
    max_bytes: int = 12_000,
) -> dict[str, str]:
    """Read a bounded set of files for model context."""
    context: dict[str, str] = {}
    total = 0
    for rel in relative_paths:
        path = workspace_root / rel
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        if total + len(content) > max_bytes:
            remaining = max(0, max_bytes - total)
            context[rel] = content[:remaining]
            break
        context[rel] = content
        total += len(content)
    return context


def default_context_paths(workspace_root: Path) -> list[str]:
    """Pick likely implementation targets in a workspace."""
    candidates = [
        "src/pilot_app/main.py",
        "src/main.py",
        "main.py",
        "app.py",
    ]
    existing = [path for path in candidates if (workspace_root / path).is_file()]
    if existing:
        return existing

    paths: list[str] = []
    for file_path in sorted(workspace_root.rglob("*.py")):
        rel = str(file_path.relative_to(workspace_root))
        if ".git" in file_path.parts or rel.startswith("tests/"):
            continue
        paths.append(rel)
        if len(paths) >= 3:
            break
    return paths
