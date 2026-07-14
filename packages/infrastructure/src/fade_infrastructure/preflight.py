"""Project preflight pipeline implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fade_application.ports import PreflightPort
from fade_domain.project import (
    InventorySummary,
    PreflightIssue,
    PreflightReport,
    Project,
)

from fade_infrastructure.git_reader import read_git_metadata, scan_inventory
from fade_infrastructure.settings import Settings


class PreflightService(PreflightPort):
    """Runs deterministic preflight checks on project sources."""

    def __init__(self, settings: Settings) -> None:
        self._max_files = settings.preflight_max_files
        self._max_bytes = settings.preflight_max_bytes

    async def run(self, project: Project, *, require_git: bool = True) -> PreflightReport:
        path = Path(project.source_location)
        issues: list[PreflightIssue] = []

        git = read_git_metadata(path)
        if require_git and not git.is_git_repo:
            issues.append(PreflightIssue(
                code="PROJECT_NOT_GIT_REPO",
                severity="error",
                message="Source path is not a Git repository",
            ))

        file_count, total_bytes, manifests, sensitive = scan_inventory(
            path,
            max_files=self._max_files,
            max_bytes=self._max_bytes,
        )

        if file_count > self._max_files:
            issues.append(PreflightIssue(
                code="PROJECT_INVENTORY_TOO_LARGE",
                severity="error",
                message=f"Project exceeds maximum file count ({self._max_files})",
            ))

        if total_bytes > self._max_bytes:
            issues.append(PreflightIssue(
                code="PROJECT_INVENTORY_TOO_LARGE",
                severity="error",
                message=f"Project exceeds maximum total size ({self._max_bytes} bytes)",
            ))

        if sensitive:
            issues.append(PreflightIssue(
                code="SENSITIVE_FILES_DETECTED",
                severity="warning",
                message=f"Detected {len(sensitive)} potentially sensitive file paths (names only)",
            ))

        if not manifests:
            issues.append(PreflightIssue(
                code="NO_MANIFEST_DETECTED",
                severity="warning",
                message="No standard manifest file detected (pyproject.toml, package.json, etc.)",
            ))

        if git.is_git_repo and git.dirty is True:
            issues.append(PreflightIssue(
                code="GIT_DIRTY",
                severity="warning",
                message="Git repository has uncommitted changes or merge in progress",
            ))

        status = _compute_status(issues)
        inventory = InventorySummary(
            file_count=min(file_count, self._max_files),
            total_bytes=total_bytes,
            manifest_files=manifests,
            sensitive_paths=sensitive[:20],
        )

        return PreflightReport(
            status=status,
            git=git,
            inventory=inventory,
            issues=issues,
            completed_at=datetime.now(UTC),
        )


def _compute_status(issues: list[PreflightIssue]) -> str:
    if any(i.severity == "error" for i in issues):
        return "fail"
    if any(i.severity == "warning" for i in issues):
        return "warn"
    return "pass"
