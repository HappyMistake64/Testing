"""Workspace API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from apps.api.dependencies import get_workspace_service
from fade_application.workspaces import WorkspaceService
from fade_domain.ids import ProjectId, WorkspaceId
from fade_domain.types import AutonomyLevel
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/projects", tags=["workspaces"])


class WorkspaceLeaseResponse(BaseModel):
    token: str
    job_id: str
    expires_at: datetime


class WorkspaceResponse(BaseModel):
    id: str
    project_id: str
    path: str
    strategy: str
    base_revision: str | None
    branch: str | None
    state: str
    lease: WorkspaceLeaseResponse | None = None
    file_hash_count: int = 0
    created_at: datetime | None = None


class CreateWorkspaceRequest(BaseModel):
    autonomy_level: str = Field(default="assisted")
    branch: str | None = None
    read_only: bool = False


class CreateWorkspaceResponse(BaseModel):
    job_id: str
    workspace: WorkspaceResponse


def _to_response(workspace) -> WorkspaceResponse:
    lease = None
    if workspace.lease:
        lease = WorkspaceLeaseResponse(
            token=workspace.lease.token,
            job_id=str(workspace.lease.job_id),
            expires_at=workspace.lease.expires_at,
        )
    return WorkspaceResponse(
        id=str(workspace.id),
        project_id=str(workspace.project_id),
        path=workspace.path,
        strategy=workspace.strategy.value,
        base_revision=workspace.base_revision,
        branch=workspace.branch,
        state=workspace.state.value,
        lease=lease,
        file_hash_count=len(workspace.file_hashes),
        created_at=workspace.created_at,
    )


@router.post("/{project_id}/workspaces", response_model=CreateWorkspaceResponse, status_code=201)
async def create_workspace(
    project_id: str,
    body: CreateWorkspaceRequest,
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> CreateWorkspaceResponse:
    try:
        autonomy = AutonomyLevel.from_string(body.autonomy_level)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        job, workspace = await service.create_workspace_for_project(
            ProjectId.from_string(project_id),
            autonomy_level=autonomy,
            branch=body.branch,
            read_only=body.read_only,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CreateWorkspaceResponse(
        job_id=str(job.id),
        workspace=_to_response(workspace),
    )


@router.get("/{project_id}/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    project_id: str,
    workspace_id: str,
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceResponse:
    workspace = await service.get_workspace(WorkspaceId.from_string(workspace_id))
    if workspace is None or str(workspace.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _to_response(workspace)
