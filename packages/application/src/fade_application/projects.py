"""Project use cases and application services."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fade_domain.ids import ProjectId
from fade_domain.project import (
    PreflightReport,
    Project,
    ProjectStatus,
    SourceType,
)

from fade_application.ports import (
    PathSafetyPort,
    PreflightPort,
    ProjectRepositoryPort,
)


def slugify(name: str) -> str:
    """Convert project name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-") or "project"


@dataclass(frozen=True, slots=True)
class RegisterProjectCommand:
    """Input for registering a new project."""

    name: str
    source_path: str
    tags: list[str] | None = None
    require_git: bool = True


@dataclass(frozen=True, slots=True)
class UpdateProjectCommand:
    """Input for patching project metadata."""

    name: str | None = None
    tags: list[str] | None = None
    default_branch: str | None = None


class ProjectService:
    """Application service for project registry operations."""

    def __init__(
        self,
        repository: ProjectRepositoryPort,
        path_safety: PathSafetyPort,
        preflight: PreflightPort,
    ) -> None:
        self._repository = repository
        self._path_safety = path_safety
        self._preflight = preflight

    async def list_projects(self, *, include_archived: bool = False) -> list[Project]:
        return await self._repository.list_all(include_archived=include_archived)

    async def get_project(self, project_id: ProjectId) -> Project | None:
        return await self._repository.get_by_id(project_id)

    async def register_project(self, command: RegisterProjectCommand) -> Project:
        canonical = self._path_safety.validate_and_resolve(command.source_path)

        existing = await self._repository.get_by_source_location(str(canonical))
        if existing is not None and existing.status != ProjectStatus.ARCHIVED:
            return existing

        slug = slugify(command.name)
        base_slug = slug
        counter = 1
        while await self._repository.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        project = Project(
            id=ProjectId.generate(),
            name=command.name,
            slug=slug,
            status=ProjectStatus.PREFLIGHT,
            source_type=SourceType.LOCAL_GIT if command.require_git else SourceType.LOCAL_PATH,
            source_location=str(canonical),
            default_branch=None,
            tags=command.tags or [],
            preflight_report=None,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )

        saved = await self._repository.create(project)
        report = await self._preflight.run(saved, require_git=command.require_git)
        final_status = _status_from_preflight(report, command.require_git)

        return await self._repository.update(
            saved.id,
            status=final_status,
            preflight_report=report,
            default_branch=report.git.branch,
        )

    async def update_metadata(
        self,
        project_id: ProjectId,
        command: UpdateProjectCommand,
    ) -> Project | None:
        project = await self._repository.get_by_id(project_id)
        if project is None or project.status == ProjectStatus.ARCHIVED:
            return None

        return await self._repository.update(
            project_id,
            name=command.name,
            tags=command.tags,
            default_branch=command.default_branch,
        )

    async def archive_project(self, project_id: ProjectId) -> Project | None:
        project = await self._repository.get_by_id(project_id)
        if project is None or project.status == ProjectStatus.ARCHIVED:
            return None
        return await self._repository.update(
            project_id,
            status=ProjectStatus.ARCHIVED,
            archived_at=_utc_now(),
        )


def _status_from_preflight(report: PreflightReport, require_git: bool) -> ProjectStatus:
    if report.status == "fail":
        return ProjectStatus.FAILED
    if require_git and not report.git.is_git_repo:
        return ProjectStatus.FAILED
    if report.status == "warn":
        return ProjectStatus.DEGRADED
    return ProjectStatus.READY


def _utc_now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
