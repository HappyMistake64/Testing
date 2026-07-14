"""Project analysis application service."""

from __future__ import annotations

from fade_domain.ids import ProjectId
from fade_domain.project import ProjectStatus
from fade_domain.project_profile import ProjectProfile, SymbolEntry

from fade_application.ports import ProjectAnalysisPort, ProjectRepositoryPort


class AnalysisService:
    """Use cases for project analysis and profile access."""

    def __init__(
        self,
        projects: ProjectRepositoryPort,
        analysis: ProjectAnalysisPort,
    ) -> None:
        self._projects = projects
        self._analysis = analysis

    async def analyze_project(self, project_id: ProjectId) -> ProjectProfile | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.status == ProjectStatus.ARCHIVED:
            return None
        return await self._analysis.analyze(project)

    async def get_profile(self, project_id: ProjectId) -> ProjectProfile | None:
        if await self._projects.get_by_id(project_id) is None:
            return None
        return await self._analysis.get_latest_profile(project_id)

    async def list_symbols(
        self,
        project_id: ProjectId,
        *,
        query: str | None = None,
        limit: int = 100,
    ) -> list[SymbolEntry] | None:
        if await self._projects.get_by_id(project_id) is None:
            return None
        return await self._analysis.list_symbols(project_id, query=query, limit=limit)
