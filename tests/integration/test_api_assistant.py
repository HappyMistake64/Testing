"""Assistant API integration tests: turns, approvals, memory, automations."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from apps.api.dependencies import AppState
from apps.api.main import create_app
from fade_infrastructure.database import Base
from fade_infrastructure.logging import configure_logging
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine


@pytest_asyncio.fixture
async def client(tmp_path) -> AsyncGenerator[AsyncClient, None]:
    db_file = tmp_path / "assistant_test.db"
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
        yield ac

    await application.state.fade.shutdown()
    get_settings.cache_clear()


async def _send_command(ac: AsyncClient, session_id: str, command: str, mode: str = "execute"):
    created = await ac.post(
        f"/api/v1/assistant/sessions/{session_id}/turns",
        json={"command": command, "mode": mode},
    )
    assert created.status_code == 201
    turn_id = created.json()["id"]
    executed = await ac.post(f"/api/v1/assistant/turns/{turn_id}/execute")
    assert executed.status_code == 200
    return executed.json()


class TestAssistantAPI:
    @pytest.mark.asyncio
    async def test_status_lists_tools_and_connectors(self, client) -> None:
        response = await client.get("/api/v1/assistant/status")
        assert response.status_code == 200
        body = response.json()
        assert body["paused"] is False
        tool_names = {tool["name"] for tool in body["tools"]}
        assert {"memory_store", "home_control", "calendar_list"} <= tool_names
        assert "smart_home" in body["connectors"]

    @pytest.mark.asyncio
    async def test_memory_command_roundtrip(self, client) -> None:
        session = await client.post("/api/v1/assistant/sessions", json={"title": "test"})
        assert session.status_code == 201
        session_id = session.json()["id"]

        stored = await _send_command(client, session_id, "remember I prefer green tea")
        assert stored["state"] == "completed"
        assert "Stored" in stored["response"]

        recalled = await _send_command(client, session_id, "what do you know about green tea")
        assert recalled["state"] == "completed"
        assert "green tea" in recalled["response"]

    @pytest.mark.asyncio
    async def test_device_control_requires_approval_then_resumes(self, client) -> None:
        session = await client.post("/api/v1/assistant/sessions", json={})
        session_id = session.json()["id"]

        turn = await _send_command(client, session_id, "turn on light.office")
        assert turn["state"] == "awaiting_approval"

        approvals = await client.get("/api/v1/assistant/approvals")
        assert approvals.status_code == 200
        pending = approvals.json()
        assert len(pending) == 1
        assert pending[0]["tool_name"] == "home_control"

        decision = await client.post(
            f"/api/v1/assistant/approvals/{pending[0]['id']}/approve"
        )
        assert decision.status_code == 200
        assert decision.json()["turn_requeued"] is True

        resumed = await client.post(f"/api/v1/assistant/turns/{turn['id']}/execute")
        assert resumed.status_code == 200
        assert resumed.json()["state"] == "completed"
        assert "light.office is now on" in resumed.json()["response"]

    @pytest.mark.asyncio
    async def test_denied_approval_fails_turn(self, client) -> None:
        session = await client.post("/api/v1/assistant/sessions", json={})
        session_id = session.json()["id"]

        turn = await _send_command(client, session_id, "turn off switch.heater")
        assert turn["state"] == "awaiting_approval"

        pending = (await client.get("/api/v1/assistant/approvals")).json()
        denied = await client.post(f"/api/v1/assistant/approvals/{pending[0]['id']}/deny")
        assert denied.status_code == 200

        after = await client.get(f"/api/v1/assistant/turns/{turn['id']}")
        assert after.json()["state"] == "failed"

    @pytest.mark.asyncio
    async def test_draft_mode_never_executes(self, client) -> None:
        session = await client.post("/api/v1/assistant/sessions", json={})
        session_id = session.json()["id"]

        turn = await _send_command(client, session_id, "turn on light.office", mode="draft")
        assert turn["state"] == "completed"
        assert "Draft only" in turn["response"]

        approvals = await client.get("/api/v1/assistant/approvals")
        assert approvals.json() == []

    @pytest.mark.asyncio
    async def test_emergency_stop_blocks_and_revokes(self, client) -> None:
        session = await client.post("/api/v1/assistant/sessions", json={})
        session_id = session.json()["id"]
        turn = await _send_command(client, session_id, "turn on light.office")
        assert turn["state"] == "awaiting_approval"

        stopped = await client.post(
            "/api/v1/assistant/emergency-stop",
            json={"paused": True, "reason": "test"},
        )
        assert stopped.status_code == 200
        assert stopped.json()["revoked_approvals"] == 1

        blocked = await _send_command(client, session_id, "lights")
        assert blocked["state"] == "failed"
        assert "paused" in blocked["response"]

        resumed = await client.post(
            "/api/v1/assistant/emergency-stop", json={"paused": False}
        )
        assert resumed.status_code == 200
        working = await _send_command(client, session_id, "lights")
        assert working["state"] == "completed"

    @pytest.mark.asyncio
    async def test_free_form_answer_uses_model_router(self, client) -> None:
        session = await client.post("/api/v1/assistant/sessions", json={})
        session_id = session.json()["id"]
        turn = await _send_command(
            client, session_id, "explain what the verification gate does"
        )
        assert turn["state"] == "completed"
        assert turn["response"]

    @pytest.mark.asyncio
    async def test_memory_api_crud(self, client) -> None:
        stored = await client.post(
            "/api/v1/assistant/memory", json={"content": "birthday is in May"}
        )
        assert stored.status_code == 201
        memory_id = stored.json()["id"]

        listed = await client.get("/api/v1/assistant/memory?query=birthday")
        assert any(item["id"] == memory_id for item in listed.json())

        deleted = await client.delete(f"/api/v1/assistant/memory/{memory_id}")
        assert deleted.status_code == 204

    @pytest.mark.asyncio
    async def test_automation_crud(self, client) -> None:
        created = await client.post(
            "/api/v1/assistant/automations",
            json={
                "name": "hourly lights",
                "command": "lights",
                "schedule_kind": "interval",
                "interval_seconds": 3600,
            },
        )
        assert created.status_code == 201
        automation_id = created.json()["id"]

        toggled = await client.post(
            f"/api/v1/assistant/automations/{automation_id}/toggle"
        )
        assert toggled.status_code == 200
        assert toggled.json()["enabled"] is False

        deleted = await client.delete(f"/api/v1/assistant/automations/{automation_id}")
        assert deleted.status_code == 204

    @pytest.mark.asyncio
    async def test_voice_endpoints(self, client) -> None:
        transcribed = await client.post(
            "/api/v1/assistant/voice/transcribe",
            json={"text_hint": "turn on the lights"},
        )
        assert transcribed.status_code == 200
        assert transcribed.json()["text"] == "turn on the lights"

        spoken = await client.post(
            "/api/v1/assistant/voice/speak", json={"text": "Hello owner"}
        )
        assert spoken.status_code == 200
        assert spoken.json()["provider_id"] == "local-browser"

    @pytest.mark.asyncio
    async def test_vision_endpoint_is_honest_about_capability(self, client) -> None:
        described = await client.post(
            "/api/v1/assistant/vision/describe", json={"image_b64": "aGVsbG8="}
        )
        assert described.status_code == 200
        assert "not configured" in described.json()["description"]

    @pytest.mark.asyncio
    async def test_turn_creates_durable_job(self, client) -> None:
        session = await client.post("/api/v1/assistant/sessions", json={})
        session_id = session.json()["id"]
        created = await client.post(
            f"/api/v1/assistant/sessions/{session_id}/turns",
            json={"command": "lights", "mode": "execute"},
        )
        assert created.status_code == 201
        # The system project for assistant jobs must exist.
        projects = await client.get("/api/v1/projects")
        slugs = [p["slug"] for p in projects.json()["items"]]
        assert "fade-assistant-core" in slugs
