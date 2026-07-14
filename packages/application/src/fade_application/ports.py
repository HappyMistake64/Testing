"""Application port interfaces (dependency inversion)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fade_domain.ids import ProjectId
from fade_domain.project import PreflightReport, Project, ProjectStatus


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    """Database connectivity health snapshot."""

    connected: bool
    engine: str
    wal_mode: bool | None = None
    integrity_ok: bool | None = None
    project_count: int | None = None


@dataclass(frozen=True, slots=True)
class SystemHealthSnapshot:
    """Aggregated system health for doctor/health endpoints."""

    status: str
    version: str
    environment: str
    database: DatabaseHealth
    capabilities: dict[str, bool]


class SystemHealthPort(ABC):
    """Port for system health checks."""

    @abstractmethod
    async def check_health(self) -> SystemHealthSnapshot:
        """Return current system health snapshot."""


class ProjectRepositoryPort(ABC):
    """Port for project persistence."""

    @abstractmethod
    async def count(self) -> int:
        """Return number of registered projects."""

    @abstractmethod
    async def exists_table(self) -> bool:
        """Return whether projects table is accessible."""

    @abstractmethod
    async def list_all(self, *, include_archived: bool = False) -> list[Project]:
        """List all projects."""

    @abstractmethod
    async def get_by_id(self, project_id: ProjectId) -> Project | None:
        """Get project by ID."""

    @abstractmethod
    async def get_by_source_location(self, source_location: str) -> Project | None:
        """Get project by canonical source path."""

    @abstractmethod
    async def slug_exists(self, slug: str) -> bool:
        """Check if slug is taken."""

    @abstractmethod
    async def create(self, project: Project) -> Project:
        """Persist new project."""

    @abstractmethod
    async def update(
        self,
        project_id: ProjectId,
        *,
        name: str | None = None,
        slug: str | None = None,
        status: ProjectStatus | None = None,
        source_type: str | None = None,
        default_branch: str | None = None,
        tags: list[str] | None = None,
        preflight_report: PreflightReport | None = None,
        archived_at: datetime | None = None,
    ) -> Project:
        """Update project fields."""


class PathSafetyPort(ABC):
    """Port for validating and resolving project source paths."""

    @abstractmethod
    def validate_and_resolve(self, source_path: str) -> Path:
        """Validate path safety and return canonical resolved path."""


class PreflightPort(ABC):
    """Port for running project preflight checks."""

    @abstractmethod
    async def run(self, project: Project, *, require_git: bool = True) -> PreflightReport:
        """Run preflight pipeline on project source."""
