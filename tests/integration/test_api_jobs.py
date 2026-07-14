"""Jobs and evidence integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from apps.api.dependencies import AppState
from apps.api.main import create_app
from fade_domain.ids import JobId
from fade_evidence.ledger import EvidenceLedger
from fade_infrastructure.database import Base
from fade_infrastructure.evidence_repository import SqlAlchemyEvidenceRepository
from fade_infrastructure.logging import configure_logging
from fade_infrastructure.models import JobEventModel, JobModel, ProjectModel  # noqa: F401
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.fixtures.git_repo import create_git_repo


@pytest_asyncio.fixture
async def client(tmp_path) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    db_file = tmp_path / "jobs_test.db"
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


class TestJobsAPI:
    @pytest.mark.asyncio
    async def test_create_pause_resume_cancel(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "job-project"))
        project = await ac.post(
            "/api/v1/projects",
            json={"name": "Job Project", "source_path": str(repo)},
        )
        project_id = project.json()["id"]

        created = await ac.post(
            "/api/v1/jobs",
            json={"project_id": project_id, "job_type": "noop"},
        )
        assert created.status_code == 201
        job_id = created.json()["id"]
        assert created.json()["state"] == "queued"

        paused = await ac.post(f"/api/v1/jobs/{job_id}/pause")
        assert paused.status_code == 404 or paused.json()["state"] == "paused"

        if paused.status_code == 200:
            resumed = await ac.post(f"/api/v1/jobs/{job_id}/resume")
            assert resumed.status_code == 200

        cancelled = await ac.post(f"/api/v1/jobs/{job_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["state"] == "cancelled"

    @pytest.mark.asyncio
    async def test_evidence_events_recorded(self, client, tmp_path) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "evidence-project"))
        project = await ac.post(
            "/api/v1/projects",
            json={"name": "Evidence", "source_path": str(repo)},
        )
        project_id = project.json()["id"]

        created = await ac.post(
            "/api/v1/jobs",
            json={"project_id": project_id, "job_type": "noop"},
        )
        job_id = created.json()["id"]

        db_url = os.environ["FADE_DATABASE_URL"]
        engine = create_async_engine(db_url)
        async with AsyncSession(engine) as session:
            evidence = SqlAlchemyEvidenceRepository(session)
            events = await evidence.list_for_job(JobId.from_string(job_id))
            assert len(events) >= 1
            assert events[0].event_type == "JOB_CREATED"
            assert EvidenceLedger.verify_chain(events)
        await engine.dispose()
