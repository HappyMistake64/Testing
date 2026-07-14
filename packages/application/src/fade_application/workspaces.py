"""Workspace application service."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fade_domain.ids import JobId, ProjectId, WorkspaceId
from fade_domain.job import Job, JobState
from fade_domain.types import AutonomyLevel
from fade_domain.workspace import Workspace, WorkspaceState
from fade_infrastructure.job_repository import SqlAlchemyJobRepository
from fade_infrastructure.project_repository import SqlAlchemyProjectRepository
from fade_infrastructure.workspace_manager import WorkspaceManager
from fade_infrastructure.workspace_repository import SqlAlchemyWorkspaceRepository


class WorkspaceService:
    """Orchestrates workspace creation and lifecycle."""

    def __init__(
        self,
        *,
        workspace_manager: WorkspaceManager,
        project_repository: SqlAlchemyProjectRepository,
        workspace_repository: SqlAlchemyWorkspaceRepository,
        job_repository: SqlAlchemyJobRepository,
    ) -> None:
        self._manager = workspace_manager
        self._projects = project_repository
        self._workspaces = workspace_repository
        self._jobs = job_repository

    async def create_workspace_for_project(
        self,
        project_id: ProjectId,
        *,
        autonomy_level: AutonomyLevel = AutonomyLevel.ASSISTED,
        branch: str | None = None,
        read_only: bool = False,
    ) -> tuple[Job, Workspace]:
        project = await self._projects.get_by_id(project_id)
        if project is None:
            raise ValueError("Project not found")

        job_id = JobId.generate()
        workspace_id = WorkspaceId.generate()
        now = datetime.now(UTC)

        job = Job(
            id=job_id,
            project_id=project_id,
            job_type="workspace",
            state=JobState.PREPARING,
            autonomy_level=autonomy_level,
            payload={"workspace_id": str(workspace_id)},
            worker_id=None,
            lease_expires_at=None,
            created_at=now,
            updated_at=now,
            checkpoint={"workspace_id": str(workspace_id)},
        )
        await self._jobs.create(job)

        workspace = self._manager.create_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
            source_path=Path(project.source_location),
            job_id=job_id,
            branch=branch or project.default_branch,
            read_only=read_only,
        )
        workspace = Workspace(
            id=workspace.id,
            project_id=workspace.project_id,
            path=workspace.path,
            strategy=workspace.strategy,
            base_revision=workspace.base_revision,
            branch=workspace.branch,
            state=WorkspaceState.READY,
            lease=workspace.lease,
            file_hashes=workspace.file_hashes,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        await self._workspaces.create(workspace, job_id=job_id)

        updated_job = Job(
            id=job.id,
            project_id=job.project_id,
            job_type=job.job_type,
            state=JobState.RUNNING,
            autonomy_level=job.autonomy_level,
            payload=job.payload,
            worker_id=job.worker_id,
            lease_expires_at=job.lease_expires_at,
            created_at=job.created_at,
            updated_at=datetime.now(UTC),
            checkpoint=job.checkpoint,
            budgets=job.budgets,
        )
        await self._jobs.update(updated_job)
        return updated_job, workspace

    async def get_workspace(self, workspace_id: WorkspaceId) -> Workspace | None:
        return await self._workspaces.get_by_id(workspace_id)

    async def release_workspace(self, workspace_id: WorkspaceId) -> Workspace | None:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            return None
        released = self._manager.release_workspace(workspace)
        return await self._workspaces.update(released)
