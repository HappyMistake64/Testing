"""Patch application with base hash validation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

PROTECTED_SEGMENTS = frozenset({".env", ".ssh", "credentials", "secrets"})


class PatchEngineError(Exception):
    """Raised when patch validation or application fails."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class FileOperation:
    path: str
    old_content: str | None
    new_content: str


@dataclass(frozen=True, slots=True)
class PatchHunk:
    path: str
    base_hash: str
    operations: list[FileOperation]


@dataclass(frozen=True, slots=True)
class ApplyPatchResult:
    applied_files: list[str]
    skipped_files: list[str]
    new_hashes: dict[str, str] = field(default_factory=dict)


def file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class PatchEngine:
    """Applies structured patches with base hash verification."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root.resolve()

    def compute_hashes(self, paths: list[str] | None = None) -> dict[str, str]:
        hashes: dict[str, str] = {}
        if paths is None:
            for file_path in self._root.rglob("*"):
                if file_path.is_file() and not self._is_under_git(file_path):
                    rel = str(file_path.relative_to(self._root))
                    hashes[rel] = file_hash(file_path.read_text(encoding="utf-8", errors="replace"))
        else:
            for rel in paths:
                resolved = self._resolve(rel)
                if resolved.is_file():
                    hashes[rel] = file_hash(
                        resolved.read_text(encoding="utf-8", errors="replace"),
                    )
        return hashes

    def apply_hunks(self, hunks: list[PatchHunk]) -> ApplyPatchResult:
        applied: list[str] = []
        skipped: list[str] = []
        new_hashes: dict[str, str] = {}

        for hunk in hunks:
            self._check_protected(hunk.path)
            resolved = self._resolve(hunk.path)
            current = ""
            if resolved.exists():
                current = resolved.read_text(encoding="utf-8", errors="replace")

            current_hash = file_hash(current)
            if current_hash != hunk.base_hash and hunk.base_hash != file_hash(""):
                raise PatchEngineError(
                    "BASE_HASH_MISMATCH",
                    (
                        f"Base hash mismatch for {hunk.path}: "
                        f"expected {hunk.base_hash}, got {current_hash}"
                    ),
                )

            if hunk.operations:
                final_content = hunk.operations[-1].new_content
            else:
                skipped.append(hunk.path)
                continue

            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(final_content, encoding="utf-8")
            applied.append(hunk.path)
            new_hashes[hunk.path] = file_hash(final_content)

        return ApplyPatchResult(
            applied_files=applied,
            skipped_files=skipped,
            new_hashes=new_hashes,
        )

    def apply_unified_diff(self, diff_text: str, base_hashes: dict[str, str]) -> ApplyPatchResult:
        hunks = parse_unified_diff(diff_text, base_hashes)
        return self.apply_hunks(hunks)

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self._root / relative_path).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise PatchEngineError(
                "PATH_ESCAPE",
                f"Path escapes workspace: {relative_path}",
            ) from exc
        return candidate

    def _check_protected(self, relative_path: str) -> None:
        parts = {part.lower() for part in Path(relative_path).parts}
        if parts & PROTECTED_SEGMENTS:
            raise PatchEngineError(
                "PROTECTED_PATH",
                f"Cannot patch protected path: {relative_path}",
            )

    def _is_under_git(self, path: Path) -> bool:
        return ".git" in path.parts


def parse_unified_diff(diff_text: str, base_hashes: dict[str, str]) -> list[PatchHunk]:
    """Parse a minimal unified diff into patch hunks."""
    hunks: list[PatchHunk] = []
    file_pattern = re.compile(r"^\+\+\+ b/(.*)$")
    current_path: str | None = None
    current_lines: list[str] = []

    for line in diff_text.splitlines():
        file_match = file_pattern.match(line)
        if file_match:
            if current_path is not None:
                hunks.append(_hunk_from_lines(current_path, current_lines, base_hashes))
            current_path = file_match.group(1)
            current_lines = []
            continue
        if current_path and (line.startswith("+") or line.startswith(" ") or line.startswith("-")):
            if line.startswith("+++") or line.startswith("---"):
                continue
            current_lines.append(line)

    if current_path is not None:
        hunks.append(_hunk_from_lines(current_path, current_lines, base_hashes))

    return hunks


def _hunk_from_lines(
    path: str,
    diff_lines: list[str],
    base_hashes: dict[str, str],
) -> PatchHunk:
    new_lines: list[str] = []
    for line in diff_lines:
        if line.startswith("+") or line.startswith(" "):
            new_lines.append(line[1:])
    new_content = "\n".join(new_lines)
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    base_hash = base_hashes.get(path, file_hash(""))
    return PatchHunk(
        path=path,
        base_hash=base_hash,
        operations=[
            FileOperation(path=path, old_content=None, new_content=new_content),
        ],
    )
