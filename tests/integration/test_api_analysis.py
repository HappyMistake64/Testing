"""Analysis API integration tests."""

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
    ProjectModel,
    ProjectProfileModel,
    SymbolIndexModel,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.fixtures.git_repo import create_git_repo


@pytest_asyncio.fixture
async def client(tmp_path) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    db_file = tmp_path / "analysis_test.db"
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


class TestAnalysisAPI:
    @pytest.mark.asyncio
    async def test_analyze_and_get_profile(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "analyze-me"))
        (repo / "service.py").write_text("def serve():\n    return True\n", encoding="utf-8")

        created = await ac.post(
            "/api/v1/projects",
            json={"name": "Analyze Me", "source_path": str(repo)},
        )
        project_id = created.json()["id"]

        analyze_resp = await ac.post(f"/api/v1/projects/{project_id}/analyze")
        assert analyze_resp.status_code == 201
        profile = analyze_resp.json()
        assert profile["version"] == 1
        assert "python" in profile["languages"]
        assert profile["symbol_count"] >= 1

        get_resp = await ac.get(f"/api/v1/projects/{project_id}/profile")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == profile["id"]

    @pytest.mark.asyncio
    async def test_list_symbols(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "symbols"))
        (repo / "lib.py").write_text("def helper():\n    pass\n", encoding="utf-8")

        created = await ac.post(
            "/api/v1/projects",
            json={"name": "Symbols", "source_path": str(repo)},
        )
        project_id = created.json()["id"]
        await ac.post(f"/api/v1/projects/{project_id}/analyze")

        symbols_resp = await ac.get(f"/api/v1/projects/{project_id}/symbols")
        assert symbols_resp.status_code == 200
        data = symbols_resp.json()
        assert data["total"] >= 1
        assert any(item["name"] == "helper" for item in data["items"])

    @pytest.mark.asyncio
    async def test_analyze_unknown_project(self, client) -> None:
        ac, _ = client
        resp = await ac.post("/api/v1/projects/01ARZ3NDEKTSV4RRFFQ69G5FAV/analyze")
        assert resp.status_code == 404
