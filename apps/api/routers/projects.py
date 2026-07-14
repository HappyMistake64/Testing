"""Projects API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from apps.api.dependencies import get_analysis_service, get_goal_service, get_project_service
from fade_application.analysis import AnalysisService
from fade_application.planning import GoalApplicationService
from fade_application.projects import ProjectService, RegisterProjectCommand, UpdateProjectCommand
from fade_domain.ids import ProjectId
from fade_infrastructure.path_safety import PathSafetyError
from fade_planning.goal_service import CreateGoalCommand
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


class HealthComponentResponse(BaseModel):
    name: str
    status: str
    message: str
    evidence: dict[str, object] = Field(default_factory=dict)


class ProjectHealthResponse(BaseModel):
    project_id: str
    components: list[HealthComponentResponse]


class ProjectProfileResponse(BaseModel):
    id: str
    project_id: str
    version: int
    revision: str | None
    languages: list[str]
    frameworks: list[str]
    commands: dict[str, str]
    file_count: int
    symbol_count: int
    created_at: datetime


class SymbolResponse(BaseModel):
    name: str
    kind: str
    line: int


class SymbolDetailResponse(BaseModel):
    name: str
    kind: str
    file_path: str
    line: int
    language: str
    content_hash: str | None = None


class SymbolListResponse(BaseModel):
    items: list[SymbolDetailResponse]
    total: int


class ExplorerNodeResponse(BaseModel):
    path: str
    is_dir: bool
    size_bytes: int = 0
    symbols: list[SymbolResponse] = Field(default_factory=list)
    children: list[ExplorerNodeResponse] = Field(default_factory=list)


class ExplorerResponse(BaseModel):
    project_id: str
    root: ExplorerNodeResponse


class CreateGoalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    intent: str = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    priority: str = "medium"


class GoalResponse(BaseModel):
    id: str
    project_id: str
    title: str
    intent: str
    constraints: list[str]
    priority: int
    status: str
    created_at: datetime
    updated_at: datetime


class GoalListResponse(BaseModel):
    items: list[GoalResponse]


def _goal_response(goal) -> GoalResponse:
    return GoalResponse(
        id=str(goal.id),
        project_id=str(goal.project_id),
        title=goal.title,
        intent=goal.intent,
        constraints=goal.constraints,
        priority=goal.priority,
        status=goal.status.value,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def _symbols_to_tree(symbols: list) -> ExplorerNodeResponse:
    """Build a shallow explorer tree from flat symbol list."""
    by_file: dict[str, list[SymbolResponse]] = {}
    for s in symbols:
        by_file.setdefault(s.file_path, []).append(
            SymbolResponse(name=s.name, kind=s.kind, line=s.line)
        )
    children = [
        ExplorerNodeResponse(
            path=path,
            is_dir=False,
            symbols=syms,
        )
        for path, syms in sorted(by_file.items())
    ]
    return ExplorerNodeResponse(path=".", is_dir=True, children=children)


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


@router.post("/{project_id}/analyze", response_model=ProjectProfileResponse, status_code=201)
async def analyze_project(
    project_id: str,
    analysis: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> ProjectProfileResponse:
    profile = await analysis.analyze_project(ProjectId.from_string(project_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Project not found")
    commands = {k: (v[0] if v else "") for k, v in profile.commands.items()}
    return ProjectProfileResponse(
        id=str(profile.id),
        project_id=str(profile.project_id),
        version=profile.version,
        revision=profile.revision,
        languages=profile.languages,
        frameworks=profile.frameworks,
        commands=commands,
        file_count=profile.symbol_count,
        symbol_count=profile.symbol_count,
        created_at=profile.created_at,
    )


@router.get("/{project_id}/profile", response_model=ProjectProfileResponse)
async def get_project_profile(
    project_id: str,
    analysis: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> ProjectProfileResponse:
    profile = await analysis.get_profile(ProjectId.from_string(project_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile found; run analyze first")
    commands = {k: (v[0] if v else "") for k, v in profile.commands.items()}
    return ProjectProfileResponse(
        id=str(profile.id),
        project_id=str(profile.project_id),
        version=profile.version,
        revision=profile.revision,
        languages=profile.languages,
        frameworks=profile.frameworks,
        commands=commands,
        file_count=profile.symbol_count,
        symbol_count=profile.symbol_count,
        created_at=profile.created_at,
    )


@router.get("/{project_id}/health", response_model=ProjectHealthResponse)
async def get_project_health(
    project_id: str,
    analysis: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> ProjectHealthResponse:
    profile = await analysis.get_profile(ProjectId.from_string(project_id))
    if profile is None:
        return ProjectHealthResponse(project_id=project_id, components=[])
    components = [
        HealthComponentResponse(
            name="languages",
            status="pass" if profile.languages else "warn",
            message=f"Detected: {', '.join(profile.languages) or 'none'}",
        ),
        HealthComponentResponse(
            name="manifests",
            status="pass" if profile.manifests else "warn",
            message=f"{len(profile.manifests)} manifest(s) found",
            evidence={"manifests": profile.manifests},
        ),
        HealthComponentResponse(
            name="symbols",
            status="pass" if profile.symbol_count > 0 else "warn",
            message=f"{profile.symbol_count} symbols indexed",
            evidence={"symbol_count": profile.symbol_count},
        ),
    ]
    for flag in profile.risk_flags:
        components.append(
            HealthComponentResponse(name="risk", status="warn", message=flag),
        )
    return ProjectHealthResponse(project_id=project_id, components=components)


@router.get("/{project_id}/explorer", response_model=ExplorerResponse)
async def get_project_explorer(
    project_id: str,
    analysis: Annotated[AnalysisService, Depends(get_analysis_service)],
    q: str | None = Query(default=None, description="Filter symbols by name"),
) -> ExplorerResponse:
    symbols = await analysis.list_symbols(
        ProjectId.from_string(project_id),
        query=q,
        limit=1000,
    )
    if symbols is None:
        raise HTTPException(status_code=404, detail="Project not found")
    root = _symbols_to_tree(symbols)
    return ExplorerResponse(project_id=project_id, root=root)


@router.get("/{project_id}/symbols", response_model=SymbolListResponse)
async def list_project_symbols(
    project_id: str,
    analysis: Annotated[AnalysisService, Depends(get_analysis_service)],
    q: str | None = Query(default=None, description="Filter symbols by name"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> SymbolListResponse:
    symbols = await analysis.list_symbols(
        ProjectId.from_string(project_id),
        query=q,
        limit=limit,
    )
    if symbols is None:
        raise HTTPException(status_code=404, detail="Project not found")
    items = [
        SymbolDetailResponse(
            name=s.name,
            kind=s.kind,
            file_path=s.file_path,
            line=s.line,
            language=s.language,
            content_hash=s.content_hash,
        )
        for s in symbols
    ]
    return SymbolListResponse(items=items, total=len(items))


@router.get("/{project_id}/goals", response_model=GoalListResponse)
async def list_goals(
    project_id: str,
    goals: Annotated[GoalApplicationService, Depends(get_goal_service)],
) -> GoalListResponse:
    items = await goals.list_goals(ProjectId.from_string(project_id))
    return GoalListResponse(items=[_goal_response(g) for g in items])


@router.post("/{project_id}/goals", response_model=GoalResponse, status_code=201)
async def create_goal(
    project_id: str,
    body: CreateGoalRequest,
    goals: Annotated[GoalApplicationService, Depends(get_goal_service)],
) -> GoalResponse:
    priority_map = {"low": 0, "medium": 1, "high": 2}
    goal = await goals.create_goal(
        CreateGoalCommand(
            project_id=ProjectId.from_string(project_id),
            title=body.title,
            intent=body.intent,
            constraints=body.constraints or body.acceptance_criteria,
            priority=priority_map.get(body.priority, 1),
        )
    )
    if goal is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _goal_response(goal)
