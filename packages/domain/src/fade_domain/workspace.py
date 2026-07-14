"""Workspace domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from fade_domain.ids import JobId, ProjectId, WorkspaceId


class WorkspaceStrategy(StrEnum):
    """How a workspace is materialized."""

    GIT_WORKTREE = "git_worktree"
    FILESYSTEM_COPY = "filesystem_copy"
    READ_ONLY_DIRECT = "read_only_direct"


class WorkspaceState(StrEnum):
    """Lifecycle state of a workspace."""

    CREATING = "creating"
    READY = "ready"
    LEASED = "leased"
    RELEASED = "released"
    FAILED = "failed"
    CLEANED = "cleaned"


@dataclass(slots=True)
class WorkspaceLease:
    """Fencing token lease for mutating workspace access."""

    token: str
    job_id: JobId
    expires_at: datetime


@dataclass(slots=True)
class Workspace:
    """Isolated working copy for a job."""

    id: WorkspaceId
    project_id: ProjectId
    path: str
    strategy: WorkspaceStrategy
    base_revision: str | None
    branch: str | None
    state: WorkspaceState
    lease: WorkspaceLease | None = None
    file_hashes: dict[str, str] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
