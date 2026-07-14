"""End-to-end pilot flow: register → analyze → goal → plan → job."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from apps.api.dependencies import AppState
from apps.api.main import create_app
from fade_domain.ids import JobId
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
from tests.fixtures.pilot_repo import materialize_pilot_repo


@pytest_asyncio.fixture
async def e2e_client(tmp_path) -> AsyncGenerator[tuple[AsyncClient, str, AppState], None]:
    db_file = tmp_path / "e2e.db"
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
    app_state = application.state.fade

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, str(tmp_path), app_state

    await application.state.fade.shutdown()
    get_settings.cache_clear()


class TestPilotFlow:
    @pytest.mark.asyncio
    async def test_full_pilot_flow(self, e2e_client) -> None:
        ac, root, app_state = e2e_client
        repo_path = materialize_pilot_repo(os.path.join(root, "pilot-small"))

        reg = await ac.post(
            "/api/v1/projects",
            json={"name": "Pilot Small", "source_path": str(repo_path), "tags": ["pilot"]},
        )
        assert reg.status_code == 201
        project_id = reg.json()["id"]
        assert reg.json()["status"] == "ready"

        analyze = await ac.post(f"/api/v1/projects/{project_id}/analyze")
        assert analyze.status_code == 201
        profile = analyze.json()
        assert profile["symbol_count"] > 0
        assert "python" in profile["languages"]

        health = await ac.get(f"/api/v1/projects/{project_id}/health")
        assert health.status_code == 200
        assert len(health.json()["components"]) > 0

        explorer = await ac.get(f"/api/v1/projects/{project_id}/explorer")
        assert explorer.status_code == 200
        assert explorer.json()["root"]["is_dir"] is True

        goal_resp = await ac.post(
            f"/api/v1/projects/{project_id}/goals",
            json={
                "title": "Improve greet message",
                "intent": "Extend greet() with FADE welcome text",
                "constraints": ["Minimal change only"],
                "acceptance_criteria": ["Tests pass"],
                "priority": "high",
            },
        )
        assert goal_resp.status_code == 201
        goal_id = goal_resp.json()["id"]

        plan_resp = await ac.post(f"/api/v1/plans?goal_id={goal_id}")
        assert plan_resp.status_code == 201
        plan_id = plan_resp.json()["id"]
        assert len(plan_resp.json()["steps"]) >= 1

        approve = await ac.post(f"/api/v1/plans/{plan_id}/approve")
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"

        job_resp = await ac.post(f"/api/v1/plans/{plan_id}/jobs")
        assert job_resp.status_code == 201
        job_id = job_resp.json()["id"]

        completed = await app_state.agent_runtime.execute_job(JobId.from_string(job_id))
        assert completed.state.value == "completed"

        job = await ac.get(f"/api/v1/jobs/{job_id}")
        assert job.status_code == 200
        assert job.json()["state"] == "completed"

        diff = await ac.get(f"/api/v1/jobs/{job_id}/diff")
        assert diff.status_code == 200
        assert len(diff.json()["files"]) > 0
        assert any("Welcome to FADE" in file["patch"] for file in diff.json()["files"])

        policies = await ac.get("/api/v1/policies")
        assert policies.status_code == 200
        assert policies.json()["items"]

        main_py = repo_path / "src" / "pilot_app" / "main.py"
        assert "Welcome to FADE" not in main_py.read_text(encoding="utf-8")
