"""API integration tests."""

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


@pytest.fixture
def test_db_url(tmp_path) -> str:
    db_file = tmp_path / "test.db"
    return f"sqlite+aiosqlite:///{db_file}"


@pytest_asyncio.fixture
async def client(test_db_url: str) -> AsyncGenerator[AsyncClient, None]:
    os.environ["FADE_DATABASE_URL"] = test_db_url
    os.environ["FADE_ENV"] = "test"

    from fade_infrastructure.settings import get_settings

    get_settings.cache_clear()

    engine = create_async_engine(test_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    application = create_app()
    settings = get_settings()
    configure_logging(settings)
    application.state.fade = AppState(settings)

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await application.state.fade.shutdown()
    get_settings.cache_clear()


class TestSystemHealth:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/system/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["version"] == "0.1.0"
        assert "database" in data
        assert data["database"]["connected"] is True
        assert data["capabilities"]["project_registry"] is False

    @pytest.mark.asyncio
    async def test_health_includes_correlation_id(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/system/health",
            headers={"X-Correlation-ID": "test-correlation-123"},
        )
        assert response.headers.get("X-Correlation-ID") == "test-correlation-123"

    @pytest.mark.asyncio
    async def test_doctor_returns_diagnostics(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/system/doctor")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("pass", "warn", "fail")
        assert "issues" in data
        assert "settings" in data
        assert data["settings"]["database_url"] == "***REDACTED***"

    @pytest.mark.asyncio
    async def test_not_found_returns_error_envelope(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NOT_FOUND"
        assert "correlation_id" in data
