"""Preflight pipeline unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fade_domain.ids import ProjectId
from fade_domain.project import Project, ProjectStatus, SourceType
from fade_infrastructure.preflight import PreflightService
from fade_infrastructure.settings import Settings
from tests.fixtures.git_repo import create_git_repo, create_non_git_project


def _make_project(path: str) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=ProjectId.generate(),
        name="Test",
        slug="test",
        status=ProjectStatus.PREFLIGHT,
        source_type=SourceType.LOCAL_GIT,
        source_location=path,
        default_branch=None,
        tags=[],
        preflight_report=None,
        created_at=now,
        updated_at=now,
    )


class TestPreflight:
    @pytest.mark.asyncio
    async def test_valid_git_repo_passes(self, tmp_path) -> None:
        repo = create_git_repo(tmp_path / "repo")
        service = PreflightService(Settings())
        report = await service.run(_make_project(str(repo)))
        assert report.git.is_git_repo is True
        assert report.git.branch == "main"
        assert report.status in ("pass", "warn")
        assert "pyproject.toml" in report.inventory.manifest_files

    @pytest.mark.asyncio
    async def test_non_git_fails_when_required(self, tmp_path) -> None:
        project_dir = create_non_git_project(tmp_path / "plain")
        service = PreflightService(Settings())
        report = await service.run(_make_project(str(project_dir)), require_git=True)
        assert report.status == "fail"
        assert any(i.code == "PROJECT_NOT_GIT_REPO" for i in report.issues)

    @pytest.mark.asyncio
    async def test_detects_sensitive_file_names(self, tmp_path) -> None:
        repo = create_git_repo(tmp_path / "secrets-repo")
        (repo / ".env").write_text("KEY=value\n", encoding="utf-8")
        service = PreflightService(Settings())
        report = await service.run(_make_project(str(repo)))
        assert ".env" in report.inventory.sensitive_paths
