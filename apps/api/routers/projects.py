"""Projects API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from apps.api.dependencies import get_project_service
from fade_application.projects import ProjectService, RegisterProjectCommand, UpdateProjectCommand
from fade_domain.ids import ProjectId
from fade_infrastructure.path_safety import PathSafetyError
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/projects", tags=["projects"])


class PreflightIssueResponse(BaseModel):
    code: str
    severity: str
    message: str


class GitMetadataResponse(BaseModel):
    is_git_repo: bool
    branch: str | None = None
    revision: str | None = None
    dirty: bool | None = None


class InventoryResponse(BaseModel):
    file_count: int
    total_bytes: int
    manifest_files: list[str] = Field(default_factory=list)
    sensitive_paths: list[str] = Field(default_factory=list)


class PreflightReportResponse(BaseModel):
    status: str
    git: GitMetadataResponse
    inventory: InventoryResponse
    issues: list[PreflightIssueResponse] = Field(default_factory=list)
    completed_at: datetime | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    source_type: str
    source_location: str
    default_branch: str | None
    tags: list[str]
    preflight: PreflightReportResponse | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int


class RegisterProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_path: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    require_git: bool = True


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    tags: list[str] | None = None
    default_branch: str | None = None


def _to_response(project) -> ProjectResponse:
    preflight = None
    if project.preflight_report:
        r = project.preflight_report
        preflight = PreflightReportResponse(
            status=r.status,
            git=GitMetadataResponse(
                is_git_repo=r.git.is_git_repo,
                branch=r.git.branch,
                revision=r.git.revision,
                dirty=r.git.dirty,
            ),
            inventory=InventoryResponse(
                file_count=r.inventory.file_count,
                total_bytes=r.inventory.total_bytes,
                manifest_files=r.inventory.manifest_files,
                sensitive_paths=r.inventory.sensitive_paths,
            ),
            issues=[
                PreflightIssueResponse(code=i.code, severity=i.severity, message=i.message)
                for i in r.issues
            ],
            completed_at=r.completed_at,
        )
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        slug=project.slug,
        status=project.status.value,
        source_type=project.source_type.value,
        source_location=project.source_location,
        default_branch=project.default_branch,
        tags=project.tags,
        preflight=preflight,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archived_at=project.archived_at,
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    service: Annotated[ProjectService, Depends(get_project_service)],
    include_archived: bool = Query(default=False),
) -> ProjectListResponse:
    projects = await service.list_projects(include_archived=include_archived)
    items = [_to_response(p) for p in projects]
    return ProjectListResponse(items=items, total=len(items))


@router.post("", response_model=ProjectResponse, status_code=201)
async def register_project(
    body: RegisterProjectRequest,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    try:
        project = await service.register_project(
            RegisterProjectCommand(
                name=body.name,
                source_path=body.source_path,
                tags=body.tags,
                require_git=body.require_git,
            )
        )
    except PathSafetyError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return _to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    project = await service.get_project(ProjectId.from_string(project_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    project = await service.update_metadata(
        ProjectId.from_string(project_id),
        UpdateProjectCommand(
            name=body.name,
            tags=body.tags,
            default_branch=body.default_branch,
        ),
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_response(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    project = await service.archive_project(ProjectId.from_string(project_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_response(project)
