"""Workspace repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fade_domain.ids import JobId, ProjectId, WorkspaceId
from fade_domain.workspace import Workspace, WorkspaceLease, WorkspaceState, WorkspaceStrategy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import WorkspaceModel


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, workspace: Workspace, *, job_id: JobId | None = None) -> Workspace:
        model = WorkspaceModel(
            id=str(workspace.id),
            project_id=str(workspace.project_id),
            job_id=(
                str(job_id)
                if job_id
                else (str(workspace.lease.job_id) if workspace.lease else None)
            ),
            path=workspace.path,
            strategy=workspace.strategy.value,
            base_revision=workspace.base_revision,
            branch=workspace.branch,
            state=workspace.state.value,
            lease_token=workspace.lease.token if workspace.lease else None,
            lease_expires_at=workspace.lease.expires_at if workspace.lease else None,
            file_hashes_json=json.dumps(workspace.file_hashes),
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)

    async def get_by_id(self, workspace_id: WorkspaceId) -> Workspace | None:
        result = await self._session.execute(
            select(WorkspaceModel).where(WorkspaceModel.id == str(workspace_id)),
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def update(self, workspace: Workspace) -> Workspace:
        result = await self._session.execute(
            select(WorkspaceModel).where(WorkspaceModel.id == str(workspace.id)),
        )
        model = result.scalar_one()
        model.path = workspace.path
        model.strategy = workspace.strategy.value
        model.base_revision = workspace.base_revision
        model.branch = workspace.branch
        model.state = workspace.state.value
        model.lease_token = workspace.lease.token if workspace.lease else None
        model.lease_expires_at = workspace.lease.expires_at if workspace.lease else None
        model.file_hashes_json = json.dumps(workspace.file_hashes)
        model.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)


def _to_domain(model: WorkspaceModel) -> Workspace:
    lease = None
    if model.lease_token and model.job_id and model.lease_expires_at:
        lease = WorkspaceLease(
            token=model.lease_token,
            job_id=JobId(model.job_id),
            expires_at=model.lease_expires_at,
        )
    return Workspace(
        id=WorkspaceId(model.id),
        project_id=ProjectId(model.project_id),
        path=model.path,
        strategy=WorkspaceStrategy(model.strategy),
        base_revision=model.base_revision,
        branch=model.branch,
        state=WorkspaceState(model.state),
        lease=lease,
        file_hashes=json.loads(model.file_hashes_json) if model.file_hashes_json else {},
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
