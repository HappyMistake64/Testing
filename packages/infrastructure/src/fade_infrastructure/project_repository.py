"""Project repository SQLAlchemy implementation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fade_application.ports import ProjectRepositoryPort
from fade_domain.ids import ProjectId
from fade_domain.project import (
    GitMetadata,
    InventorySummary,
    PreflightIssue,
    PreflightReport,
    Project,
    ProjectStatus,
    SourceType,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import ProjectModel


class SqlAlchemyProjectRepository(ProjectRepositoryPort):
    """SQLAlchemy implementation of project persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(ProjectModel).where(
                ProjectModel.status != ProjectStatus.ARCHIVED.value
            )
        )
        return result.scalar_one()

    async def exists_table(self) -> bool:
        try:
            await self.count()
            return True
        except Exception:
            return False

    async def list_all(self, *, include_archived: bool = False) -> list[Project]:
        query = select(ProjectModel).order_by(ProjectModel.created_at.desc())
        if not include_archived:
            query = query.where(ProjectModel.status != ProjectStatus.ARCHIVED.value)
        result = await self._session.execute(query)
        return [_to_domain(row) for row in result.scalars()]

    async def get_by_id(self, project_id: ProjectId) -> Project | None:
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.id == str(project_id))
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_by_source_location(self, source_location: str) -> Project | None:
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.source_location == source_location)
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def slug_exists(self, slug: str) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(ProjectModel).where(ProjectModel.slug == slug)
        )
        return result.scalar_one() > 0

    async def create(self, project: Project) -> Project:
        model = _to_model(project)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)

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
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.id == str(project_id))
        )
        model = result.scalar_one()
        if name is not None:
            model.name = name
        if slug is not None:
            model.slug = slug
        if status is not None:
            model.status = status.value
        if source_type is not None:
            model.source_type = source_type
        if default_branch is not None:
            model.default_branch = default_branch
        if tags is not None:
            model.tags = json.dumps(tags)
        if preflight_report is not None:
            model.preflight_json = _serialize_preflight(preflight_report)
        if archived_at is not None:
            model.archived_at = archived_at
        model.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)


def _to_model(project: Project) -> ProjectModel:
    return ProjectModel(
        id=str(project.id),
        name=project.name,
        slug=project.slug,
        status=project.status.value,
        source_type=project.source_type.value,
        source_location=project.source_location,
        default_branch=project.default_branch,
        tags=json.dumps(project.tags),
        preflight_json=(
            _serialize_preflight(project.preflight_report) if project.preflight_report else None
        ),
        archived_at=project.archived_at,
    )


def _to_domain(model: ProjectModel) -> Project:
    return Project(
        id=ProjectId(model.id),
        name=model.name,
        slug=model.slug,
        status=ProjectStatus(model.status),
        source_type=SourceType(model.source_type),
        source_location=model.source_location,
        default_branch=model.default_branch,
        tags=json.loads(model.tags) if model.tags else [],
        preflight_report=_deserialize_preflight(model.preflight_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
        archived_at=model.archived_at,
    )


def _serialize_preflight(report: PreflightReport) -> str:
    data: dict[str, Any] = {
        "status": report.status,
        "git": {
            "is_git_repo": report.git.is_git_repo,
            "branch": report.git.branch,
            "revision": report.git.revision,
            "dirty": report.git.dirty,
        },
        "inventory": {
            "file_count": report.inventory.file_count,
            "total_bytes": report.inventory.total_bytes,
            "manifest_files": report.inventory.manifest_files,
            "sensitive_paths": report.inventory.sensitive_paths,
        },
        "issues": [
            {"code": i.code, "severity": i.severity, "message": i.message}
            for i in report.issues
        ],
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
    }
    return json.dumps(data)


def _deserialize_preflight(raw: str | None) -> PreflightReport | None:
    if not raw:
        return None
    data = json.loads(raw)
    git_data = data["git"]
    inv_data = data["inventory"]
    completed = data.get("completed_at")
    return PreflightReport(
        status=data["status"],
        git=GitMetadata(
            is_git_repo=git_data["is_git_repo"],
            branch=git_data.get("branch"),
            revision=git_data.get("revision"),
            dirty=git_data.get("dirty"),
        ),
        inventory=InventorySummary(
            file_count=inv_data["file_count"],
            total_bytes=inv_data["total_bytes"],
            manifest_files=inv_data.get("manifest_files", []),
            sensitive_paths=inv_data.get("sensitive_paths", []),
        ),
        issues=[
            PreflightIssue(code=i["code"], severity=i["severity"], message=i["message"])
            for i in data.get("issues", [])
        ],
        completed_at=datetime.fromisoformat(completed) if completed else None,
    )
