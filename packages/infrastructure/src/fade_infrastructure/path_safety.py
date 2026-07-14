"""Path safety validation for project sources."""

from __future__ import annotations

import os
from pathlib import Path

from fade_application.ports import PathSafetyPort

from fade_infrastructure.settings import Settings


class PathSafetyError(Exception):
    """Raised when a project path fails safety checks."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class PathSafetyService(PathSafetyPort):
    """Validates and resolves project source paths within allowed roots."""

    def __init__(self, settings: Settings) -> None:
        self._allowed_roots = settings.allowed_project_roots

    def validate_and_resolve(self, source_path: str) -> Path:
        if not source_path or not source_path.strip():
            raise PathSafetyError("PROJECT_PATH_NOT_FOUND", "Source path is empty")

        raw = Path(source_path).expanduser()
        if not raw.exists():
            raise PathSafetyError("PROJECT_PATH_NOT_FOUND", f"Path does not exist: {source_path}")

        if not raw.is_dir():
            raise PathSafetyError(
                "PROJECT_PATH_NOT_FOUND",
                f"Path is not a directory: {source_path}",
            )

        try:
            resolved = raw.resolve(strict=True)
        except OSError as exc:
            raise PathSafetyError(
                "PROJECT_PATH_NOT_FOUND",
                f"Cannot resolve path: {source_path}",
            ) from exc

        self._check_allowed_roots(resolved)
        self._check_symlink_containment(raw, resolved)

        return resolved

    def _check_allowed_roots(self, resolved: Path) -> None:
        if not self._allowed_roots:
            return

        for root_str in self._allowed_roots:
            root = Path(root_str).expanduser().resolve()
            try:
                resolved.relative_to(root)
                return
            except ValueError:
                continue

        raise PathSafetyError(
            "PROJECT_PATH_NOT_ALLOWED",
            f"Path {resolved} is outside allowed project roots",
        )

    def _check_symlink_containment(self, raw: Path, resolved: Path) -> None:
        """Reject symlinks that resolve outside allowed roots."""
        if raw == resolved:
            return

        if self._allowed_roots:
            for root_str in self._allowed_roots:
                root = Path(root_str).expanduser().resolve()
                try:
                    resolved.relative_to(root)
                    return
                except ValueError:
                    continue
            raise PathSafetyError(
                "PROJECT_PATH_SYMLINK_ESCAPE",
                f"Symlink resolves outside allowed roots: {raw} -> {resolved}",
            )

        # No roots configured: still reject suspicious symlinks pointing outside parent
        if not os.path.isabs(str(raw)):
            return
        parent = raw.parent.resolve()
        try:
            resolved.relative_to(parent)
        except ValueError:
            raise PathSafetyError(
                "PROJECT_PATH_SYMLINK_ESCAPE",
                f"Symlink escapes parent directory: {raw} -> {resolved}",
            ) from None
