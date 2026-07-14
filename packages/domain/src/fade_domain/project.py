"""Project domain entity and related value types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from fade_domain.ids import ProjectId


class ProjectStatus(StrEnum):
    """Lifecycle status of a registered project."""

    NEW = "new"
    PREFLIGHT = "preflight"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    ARCHIVED = "archived"


class SourceType(StrEnum):
    """How the project source is referenced."""

    LOCAL_GIT = "local_git"
    LOCAL_PATH = "local_path"


@dataclass(frozen=True, slots=True)
class PreflightIssue:
    """Single preflight finding."""

    code: str
    severity: str  # info | warning | error
    message: str


@dataclass(frozen=True, slots=True)
class GitMetadata:
    """Read-only Git metadata from filesystem inspection."""

    is_git_repo: bool
    branch: str | None = None
    revision: str | None = None
    dirty: bool | None = None


@dataclass(frozen=True, slots=True)
class InventorySummary:
    """File inventory from preflight scan."""

    file_count: int
    total_bytes: int
    manifest_files: list[str] = field(default_factory=list)
    sensitive_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PreflightReport:
    """Result of project preflight pipeline."""

    status: str  # pass | warn | fail
    git: GitMetadata
    inventory: InventorySummary
    issues: list[PreflightIssue] = field(default_factory=list)
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Project:
    """Registered managed project."""

    id: ProjectId
    name: str
    slug: str
    status: ProjectStatus
    source_type: SourceType
    source_location: str
    default_branch: str | None
    tags: list[str]
    preflight_report: PreflightReport | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status != ProjectStatus.ARCHIVED
