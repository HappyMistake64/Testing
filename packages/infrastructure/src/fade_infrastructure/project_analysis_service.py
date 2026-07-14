"""Project analysis infrastructure service."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fade_application.ports import ProjectAnalysisPort
from fade_domain.ids import ProfileId, ProjectId
from fade_domain.project import Project
from fade_domain.project_profile import ProjectProfile, SymbolEntry
from fade_project_analysis.analyzer import analyze_project
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from fade_infrastructure.git_reader import read_git_metadata
from fade_infrastructure.models import ProjectProfileModel, SymbolIndexModel


class ProjectAnalysisService(ProjectAnalysisPort):
    """Filesystem-based project analysis with persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def analyze(self, project: Project) -> ProjectProfile:
        path = Path(project.source_location)
        git = read_git_metadata(path)
        result = analyze_project(path, revision=git.revision)

        version = await self._next_version(project.id)
        profile_id = ProfileId.generate()
        now = datetime.now(UTC)

        profile = ProjectProfile(
            id=profile_id,
            project_id=project.id,
            version=version,
            revision=result.revision,
            languages=result.languages,
            frameworks=result.frameworks,
            manifests=result.manifests,
            commands=result.commands,
            architecture_summary=result.architecture_summary,
            risk_flags=result.risk_flags,
            symbol_count=len(result.symbols),
            created_at=now,
            symbols=result.symbols,
        )

        await self._session.execute(
            delete(SymbolIndexModel).where(SymbolIndexModel.project_id == str(project.id))
        )
        self._session.add(
            ProjectProfileModel(
                id=str(profile_id),
                project_id=str(project.id),
                version=version,
                revision=result.revision,
                profile_json=_serialize_profile(profile),
            )
        )
        for symbol in result.symbols:
            self._session.add(
                SymbolIndexModel(
                    id=str(ULID()),
                    project_id=str(project.id),
                    profile_version=version,
                    name=symbol.name,
                    kind=symbol.kind,
                    file_path=symbol.file_path,
                    line=symbol.line,
                    language=symbol.language,
                    content_hash=symbol.content_hash,
                )
            )
        await self._session.commit()
        return profile

    async def get_latest_profile(self, project_id: ProjectId) -> ProjectProfile | None:
        result = await self._session.execute(
            select(ProjectProfileModel)
            .where(ProjectProfileModel.project_id == str(project_id))
            .order_by(ProjectProfileModel.version.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        symbols = await self.list_symbols(project_id, limit=10_000)
        return _deserialize_profile(row, symbols)

    async def list_symbols(
        self,
        project_id: ProjectId,
        *,
        query: str | None = None,
        limit: int = 100,
    ) -> list[SymbolEntry]:
        stmt = (
            select(SymbolIndexModel)
            .where(SymbolIndexModel.project_id == str(project_id))
            .order_by(SymbolIndexModel.file_path, SymbolIndexModel.line)
            .limit(limit)
        )
        if query:
            stmt = stmt.where(SymbolIndexModel.name.contains(query))
        result = await self._session.execute(stmt)
        return [_symbol_to_domain(row) for row in result.scalars()]

    async def _next_version(self, project_id: ProjectId) -> int:
        result = await self._session.execute(
            select(func.max(ProjectProfileModel.version)).where(
                ProjectProfileModel.project_id == str(project_id)
            )
        )
        current = result.scalar_one_or_none()
        return (current or 0) + 1


def _serialize_profile(profile: ProjectProfile) -> str:
    data = {
        "languages": profile.languages,
        "frameworks": profile.frameworks,
        "manifests": profile.manifests,
        "commands": profile.commands,
        "architecture_summary": profile.architecture_summary,
        "risk_flags": profile.risk_flags,
        "symbol_count": profile.symbol_count,
    }
    return json.dumps(data)


def _deserialize_profile(model: ProjectProfileModel, symbols: list[SymbolEntry]) -> ProjectProfile:
    data = json.loads(model.profile_json)
    return ProjectProfile(
        id=ProfileId(model.id),
        project_id=ProjectId(model.project_id),
        version=model.version,
        revision=model.revision,
        languages=data.get("languages", []),
        frameworks=data.get("frameworks", []),
        manifests=data.get("manifests", []),
        commands=data.get("commands", {}),
        architecture_summary=data.get("architecture_summary"),
        risk_flags=data.get("risk_flags", []),
        symbol_count=data.get("symbol_count", len(symbols)),
        created_at=model.created_at,
        symbols=symbols,
    )


def _symbol_to_domain(model: SymbolIndexModel) -> SymbolEntry:
    return SymbolEntry(
        name=model.name,
        kind=model.kind,
        file_path=model.file_path,
        line=model.line,
        language=model.language,
        content_hash=model.content_hash,
    )
