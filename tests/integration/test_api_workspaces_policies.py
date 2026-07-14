"""Workspace and policy API integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from apps.api.dependencies import AppState
from apps.api.main import create_app
from fade_infrastructure.database import Base
from fade_infrastructure.logging import configure_logging
from fade_infrastructure.models import (  # noqa: F401
    ApprovalModel,
    ArtifactModel,
    GoalModel,
    JobEventModel,
    JobModel,
    PlanModel,
    PolicyModel,
    ProjectModel,
    ProjectProfileModel,
    SymbolIndexModel,
    WorkspaceModel,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.fixtures.git_repo import create_git_repo


@pytest_asyncio.fixture
async def client(tmp_path) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    db_file = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    os.environ["FADE_DATABASE_URL"] = db_url
    os.environ["FADE_ENV"] = "test"
    os.environ["FADE_PROJECT_ALLOWED_ROOTS"] = str(tmp_path)

    from fade_infrastructure.settings import get_settings

    get_settings.cache_clear()

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    application = create_app()
    settings = get_settings()
    configure_logging(settings)
    application.state.fade = AppState(settings)

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, str(tmp_path)

    await application.state.fade.shutdown()
    get_settings.cache_clear()


class TestWorkspaceAPI:
    @pytest.mark.asyncio
    async def test_create_workspace_for_project(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "ws-project"))
        project = await ac.post(
            "/api/v1/projects",
            json={"name": "WS Project", "source_path": str(repo)},
        )
        project_id = project.json()["id"]

        response = await ac.post(
            f"/api/v1/projects/{project_id}/workspaces",
            json={"autonomy_level": "assisted"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["job_id"]
        assert data["workspace"]["state"] == "ready"
        assert data["workspace"]["lease"]["token"]


class TestPoliciesAPI:
    @pytest.mark.asyncio
    async def test_list_and_effective_policies(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "policy-project"))
        project = await ac.post(
            "/api/v1/projects",
            json={"name": "Policy Project", "source_path": str(repo)},
        )
        project_id = project.json()["id"]

        policies = await ac.get("/api/v1/policies")
        assert policies.status_code == 200
        assert policies.json()["total"] >= 1

        effective = await ac.get(f"/api/v1/projects/{project_id}/policies/effective")
        assert effective.status_code == 200
        body = effective.json()
        assert body["autonomy_level"] == "assisted"
        assert "git" in body["allowed_commands"]
