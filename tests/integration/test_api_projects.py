"""Projects API integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from apps.api.dependencies import AppState
from apps.api.main import create_app
from fade_infrastructure.database import Base
from fade_infrastructure.logging import configure_logging
from fade_infrastructure.models import ProjectModel  # noqa: F401
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.fixtures.git_repo import create_git_repo, create_non_git_project


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


class TestProjectsAPI:
    @pytest.mark.asyncio
    async def test_register_valid_git_project(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "valid-repo"))

        response = await ac.post(
            "/api/v1/projects",
            json={"name": "Valid Repo", "source_path": str(repo), "tags": ["test"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Valid Repo"
        assert data["status"] == "ready"
        assert data["preflight"]["git"]["is_git_repo"] is True
        assert "pyproject.toml" in data["preflight"]["inventory"]["manifest_files"]

    @pytest.mark.asyncio
    async def test_register_idempotent_by_path(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "idempotent"))

        r1 = await ac.post(
            "/api/v1/projects",
            json={"name": "First", "source_path": str(repo)},
        )
        r2 = await ac.post(
            "/api/v1/projects",
            json={"name": "Second", "source_path": str(repo)},
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]

    @pytest.mark.asyncio
    async def test_reject_path_outside_roots(self, tmp_path) -> None:
        outside = create_git_repo(tmp_path / "outside")
        allowed = tmp_path / "allowed"
        allowed.mkdir()

        db_file = tmp_path / "restricted.db"
        db_url = f"sqlite+aiosqlite:///{db_file}"
        os.environ["FADE_DATABASE_URL"] = db_url
        os.environ["FADE_PROJECT_ALLOWED_ROOTS"] = str(allowed)

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
            response = await ac.post(
                "/api/v1/projects",
                json={"name": "Bad Path", "source_path": str(outside)},
            )
            assert response.status_code == 400

        await application.state.fade.shutdown()
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_reject_non_git_when_required(self, client) -> None:
        ac, root = client
        plain = create_non_git_project(os.path.join(root, "no-git"))

        response = await ac.post(
            "/api/v1/projects",
            json={"name": "No Git", "source_path": str(plain)},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "failed"

    @pytest.mark.asyncio
    async def test_list_and_get_project(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "listed"))

        created = await ac.post(
            "/api/v1/projects",
            json={"name": "Listed", "source_path": str(repo)},
        )
        project_id = created.json()["id"]

        list_resp = await ac.get("/api/v1/projects")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

        get_resp = await ac.get(f"/api/v1/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["slug"] == "listed"

    @pytest.mark.asyncio
    async def test_archive_project(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "to-archive"))

        created = await ac.post(
            "/api/v1/projects",
            json={"name": "Archive Me", "source_path": str(repo)},
        )
        project_id = created.json()["id"]

        archive_resp = await ac.post(f"/api/v1/projects/{project_id}/archive")
        assert archive_resp.status_code == 200
        assert archive_resp.json()["status"] == "archived"

        list_resp = await ac.get("/api/v1/projects")
        assert all(p["id"] != project_id for p in list_resp.json()["items"])

    @pytest.mark.asyncio
    async def test_original_project_unchanged(self, client) -> None:
        ac, root = client
        repo = create_git_repo(os.path.join(root, "unchanged"))
        readme = repo / "README.md"
        original_content = readme.read_text(encoding="utf-8")

        await ac.post(
            "/api/v1/projects",
            json={"name": "Unchanged", "source_path": str(repo)},
        )

        assert readme.read_text(encoding="utf-8") == original_content
