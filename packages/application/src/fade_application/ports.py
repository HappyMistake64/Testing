"""Application port interfaces (dependency inversion)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fade_domain.evidence import EvidenceEvent
from fade_domain.goal import Goal
from fade_domain.ids import GoalId, JobId, PlanId, ProjectId
from fade_domain.job import Job
from fade_domain.plan import Plan, PlanStatus
from fade_domain.project import PreflightReport, Project, ProjectStatus
from fade_domain.project_profile import ProjectProfile, SymbolEntry


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


class ProjectAnalysisPort(ABC):
    """Port for project source analysis."""

    @abstractmethod
    async def analyze(self, project: Project) -> ProjectProfile:
        """Run analysis and persist profile."""

    @abstractmethod
    async def get_latest_profile(self, project_id: ProjectId) -> ProjectProfile | None:
        """Get latest profile for project."""

    @abstractmethod
    async def list_symbols(
        self,
        project_id: ProjectId,
        *,
        query: str | None = None,
        limit: int = 100,
    ) -> list[SymbolEntry]:
        """List indexed symbols for project."""


class JobRepositoryPort(ABC):
    """Port for job persistence."""

    @abstractmethod
    async def create(self, job: Job) -> Job:
        """Persist new job."""

    @abstractmethod
    async def get_by_id(self, job_id: JobId) -> Job | None:
        """Get job by ID."""

    @abstractmethod
    async def update(self, job: Job) -> Job:
        """Update job record."""

    @abstractmethod
    async def list_by_project(self, project_id: ProjectId) -> list[Job]:
        """List jobs for a project."""


class JobQueuePort(ABC):
    """Port for durable job queue operations."""

    @abstractmethod
    async def claim_next(self, worker_id: str, *, lease_seconds: int = 60) -> Job | None:
        """Claim next queued job for worker."""

    @abstractmethod
    async def heartbeat(self, job_id: JobId, worker_id: str, *, lease_seconds: int = 60) -> bool:
        """Renew job lease."""

    @abstractmethod
    async def release_stale(self, *, grace_seconds: int = 120) -> int:
        """Requeue jobs with expired leases. Returns count affected."""


class EvidencePort(ABC):
    """Port for evidence ledger persistence."""

    @abstractmethod
    async def append(self, event: EvidenceEvent) -> EvidenceEvent:
        """Append event to ledger."""

    @abstractmethod
    async def list_for_job(self, job_id: JobId) -> list[EvidenceEvent]:
        """List events for a job in sequence order."""

    @abstractmethod
    async def list_since(self, job_id: JobId, after_sequence: int) -> list[EvidenceEvent]:
        """List events after sequence for SSE streaming."""


class GoalRepositoryPort(ABC):
    """Port for goal persistence."""

    @abstractmethod
    async def create(self, goal: Goal) -> Goal:
        """Persist goal."""

    @abstractmethod
    async def get_by_id(self, goal_id: GoalId) -> Goal | None:
        """Get goal by ID."""

    @abstractmethod
    async def list_by_project(self, project_id: ProjectId) -> list[Goal]:
        """List goals for project."""

    @abstractmethod
    async def update(self, goal: Goal) -> Goal:
        """Update goal."""


class PlanRepositoryPort(ABC):
    """Port for plan persistence."""

    @abstractmethod
    async def create(self, plan: Plan) -> Plan:
        """Persist plan."""

    @abstractmethod
    async def get_by_id(self, plan_id: PlanId) -> Plan | None:
        """Get plan by ID."""

    @abstractmethod
    async def list_by_goal(self, goal_id: GoalId) -> list[Plan]:
        """List plans for goal."""

    @abstractmethod
    async def update_status(self, plan_id: PlanId, status: PlanStatus) -> Plan | None:
        """Update plan status."""
