"""Unit tests for the assistant: intents, approvals, memory, automations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fade_agent_runtime.assistant_intents import interpret
from fade_agent_runtime.assistant_tools import (
    ApprovalRequired,
    AssistantPaused,
    AssistantToolRegistry,
    normalize_args_hash,
)
from fade_domain.assistant import (
    AssistantSession,
    AssistantTurn,
    CommandMode,
    MemoryItem,
    TurnState,
)
from fade_domain.ids import ApprovalId, AssistantSessionId, AssistantTurnId, MemoryId
from fade_infrastructure.assistant_repository import SqlAlchemyAssistantRepository
from fade_infrastructure.automation_repository import SqlAlchemyAutomationRepository
from fade_infrastructure.connectors import ConnectorRegistry
from fade_infrastructure.database import Base
from fade_infrastructure.memory_repository import SqlAlchemyMemoryRepository
from fade_infrastructure.settings import Settings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/assistant.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path}/assistant.db",
        env="test",
    )


async def _make_turn(
    repo: SqlAlchemyAssistantRepository, *, command: str = "test"
) -> AssistantTurn:
    now = datetime.now(UTC)
    session = AssistantSession(
        id=AssistantSessionId.generate(),
        title="t",
        provider_id=None,
        model_id=None,
        created_at=now,
        updated_at=now,
    )
    await repo.create_session(session)
    turn = AssistantTurn(
        id=AssistantTurnId.generate(),
        session_id=session.id,
        command=command,
        mode=CommandMode.EXECUTE,
        state=TurnState.QUEUED,
        provider_id=None,
        model_id=None,
        response=None,
        created_at=now,
        updated_at=now,
    )
    return await repo.create_turn(turn)


# ---------------------------------------------------------------------------
# Intent interpretation
# ---------------------------------------------------------------------------


class TestIntents:
    def test_remember_command(self) -> None:
        intent = interpret("remember I prefer green tea")
        assert intent.kind == "tools"
        assert intent.tool_calls[0]["tool"] == "memory_store"
        assert intent.tool_calls[0]["args"]["content"] == "I prefer green tea"

    def test_czech_remember_command(self) -> None:
        intent = interpret("zapamatuj si moje auto je modré")
        assert intent.tool_calls[0]["tool"] == "memory_store"

    def test_recall_command(self) -> None:
        intent = interpret("what do you know about tea")
        assert intent.tool_calls[0]["tool"] == "memory_search"

    def test_turn_on_light(self) -> None:
        intent = interpret("turn on light.office")
        assert intent.tool_calls[0]["tool"] == "home_control"
        assert intent.tool_calls[0]["args"] == {
            "entity_id": "light.office",
            "service": "turn_on",
        }

    def test_turn_on_bare_name_defaults_to_light_domain(self) -> None:
        intent = interpret("zapni office")
        assert intent.tool_calls[0]["args"]["entity_id"] == "light.office"

    def test_calendar_command(self) -> None:
        intent = interpret("what's on my calendar")
        assert intent.tool_calls[0]["tool"] == "calendar_list"

    def test_notify_command(self) -> None:
        intent = interpret("notify me: the build finished")
        assert intent.tool_calls[0]["tool"] == "notify_send"

    def test_free_form_falls_back_to_answer(self) -> None:
        intent = interpret("explain how the verification gate works")
        assert intent.kind == "answer"
        assert intent.tool_calls == []


# ---------------------------------------------------------------------------
# Approval binding
# ---------------------------------------------------------------------------


class TestApprovals:
    def test_normalized_hash_is_stable_and_arg_sensitive(self) -> None:
        one = normalize_args_hash("home_control", {"entity_id": "light.a", "service": "turn_on"})
        two = normalize_args_hash("home_control", {"service": "turn_on", "entity_id": "light.a"})
        other = normalize_args_hash(
            "home_control", {"entity_id": "light.b", "service": "turn_on"}
        )
        assert one == two
        assert one != other

    @pytest.mark.asyncio
    async def test_device_control_requires_approval_then_executes(
        self, session_factory, tmp_path
    ) -> None:
        registry = AssistantToolRegistry(connectors=ConnectorRegistry(_settings(tmp_path)))
        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            memory = SqlAlchemyMemoryRepository(session)
            turn = await _make_turn(repo)

            with pytest.raises(ApprovalRequired) as exc_info:
                await registry.execute(
                    tool_name="home_control",
                    args={"entity_id": "light.office", "service": "turn_on"},
                    turn_id=turn.id,
                    repository=repo,
                    memory=memory,
                )

            approval_id = ApprovalId.from_string(exc_info.value.approval_id)
            decided = await repo.decide_approval(approval_id, decision="approved")
            assert decided is not None

            result = await registry.execute(
                tool_name="home_control",
                args={"entity_id": "light.office", "service": "turn_on"},
                turn_id=turn.id,
                repository=repo,
                memory=memory,
            )
            assert result == {"entity_id": "light.office", "state": "on"}

    @pytest.mark.asyncio
    async def test_approval_is_single_use(self, session_factory, tmp_path) -> None:
        registry = AssistantToolRegistry(connectors=ConnectorRegistry(_settings(tmp_path)))
        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            memory = SqlAlchemyMemoryRepository(session)
            turn = await _make_turn(repo)
            args = {"entity_id": "light.office", "service": "turn_on"}

            with pytest.raises(ApprovalRequired) as exc_info:
                await registry.execute(
                    tool_name="home_control",
                    args=args,
                    turn_id=turn.id,
                    repository=repo,
                    memory=memory,
                )
            await repo.decide_approval(
                ApprovalId.from_string(exc_info.value.approval_id), decision="approved"
            )
            await registry.execute(
                tool_name="home_control",
                args=args,
                turn_id=turn.id,
                repository=repo,
                memory=memory,
            )
            # Second identical call must request a fresh approval.
            with pytest.raises(ApprovalRequired):
                await registry.execute(
                    tool_name="home_control",
                    args=args,
                    turn_id=turn.id,
                    repository=repo,
                    memory=memory,
                )

    @pytest.mark.asyncio
    async def test_approval_does_not_transfer_to_other_args(
        self, session_factory, tmp_path
    ) -> None:
        registry = AssistantToolRegistry(connectors=ConnectorRegistry(_settings(tmp_path)))
        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            memory = SqlAlchemyMemoryRepository(session)
            turn = await _make_turn(repo)

            with pytest.raises(ApprovalRequired) as exc_info:
                await registry.execute(
                    tool_name="home_control",
                    args={"entity_id": "light.office", "service": "turn_on"},
                    turn_id=turn.id,
                    repository=repo,
                    memory=memory,
                )
            await repo.decide_approval(
                ApprovalId.from_string(exc_info.value.approval_id), decision="approved"
            )

            with pytest.raises(ApprovalRequired):
                await registry.execute(
                    tool_name="home_control",
                    args={"entity_id": "switch.heater", "service": "turn_on"},
                    turn_id=turn.id,
                    repository=repo,
                    memory=memory,
                )

    @pytest.mark.asyncio
    async def test_read_tools_execute_without_approval(self, session_factory, tmp_path) -> None:
        registry = AssistantToolRegistry(connectors=ConnectorRegistry(_settings(tmp_path)))
        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            memory = SqlAlchemyMemoryRepository(session)
            turn = await _make_turn(repo)
            result = await registry.execute(
                tool_name="home_state",
                args={"domain": "light"},
                turn_id=turn.id,
                repository=repo,
                memory=memory,
            )
            assert "states" in result

    @pytest.mark.asyncio
    async def test_emergency_stop_blocks_all_tools(self, session_factory, tmp_path) -> None:
        registry = AssistantToolRegistry(connectors=ConnectorRegistry(_settings(tmp_path)))
        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            memory = SqlAlchemyMemoryRepository(session)
            turn = await _make_turn(repo)
            await repo.set_paused(True, reason="test")

            with pytest.raises(AssistantPaused):
                await registry.execute(
                    tool_name="memory_search",
                    args={"query": "anything"},
                    turn_id=turn.id,
                    repository=repo,
                    memory=memory,
                )

    @pytest.mark.asyncio
    async def test_unknown_arguments_are_rejected(self, session_factory, tmp_path) -> None:
        registry = AssistantToolRegistry(connectors=ConnectorRegistry(_settings(tmp_path)))
        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            memory = SqlAlchemyMemoryRepository(session)
            turn = await _make_turn(repo)
            with pytest.raises(ValueError, match="Unexpected arguments"):
                await registry.execute(
                    tool_name="memory_search",
                    args={"query": "x", "evil": "yes"},
                    turn_id=turn.id,
                    repository=repo,
                    memory=memory,
                )


# ---------------------------------------------------------------------------
# Turn claim (duplicate execution guard)
# ---------------------------------------------------------------------------


class TestTurnClaim:
    def _orchestrator(self, session_factory, tmp_path):
        from fade_agent_runtime.assistant_orchestrator import AssistantOrchestrator
        from fade_model_router.router import ModelRouter
        from fade_model_router.stub_adapter import StubModelAdapter

        return AssistantOrchestrator(
            _settings(tmp_path),
            session_factory,
            ModelRouter([StubModelAdapter()]),
        )

    @pytest.mark.asyncio
    async def test_running_turn_is_not_executed_again(self, session_factory, tmp_path) -> None:
        orchestrator = self._orchestrator(session_factory, tmp_path)
        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            turn = await _make_turn(repo, command="turn on light.office")
            await repo.update_turn(turn.id, state=TurnState.RUNNING)

        state = await orchestrator.execute_turn(turn.id)
        assert state == TurnState.RUNNING

        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            assert await repo.list_pending_approvals() == []

    @pytest.mark.asyncio
    async def test_double_execution_creates_single_approval(
        self, session_factory, tmp_path
    ) -> None:
        orchestrator = self._orchestrator(session_factory, tmp_path)
        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            turn = await _make_turn(repo, command="turn on light.office")

        first = await orchestrator.execute_turn(turn.id)
        second = await orchestrator.execute_turn(turn.id)
        assert first == TurnState.AWAITING_APPROVAL
        assert second == TurnState.AWAITING_APPROVAL

        async with session_factory() as session:
            repo = SqlAlchemyAssistantRepository(session)
            assert len(await repo.list_pending_approvals()) == 1


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


class TestMemory:
    @pytest.mark.asyncio
    async def test_store_and_search(self, session_factory) -> None:
        async with session_factory() as session:
            memory = SqlAlchemyMemoryRepository(session)
            item = MemoryItem(
                id=MemoryId.generate(),
                content="The owner prefers green tea in the morning",
                source_turn_id=None,
                confidence="user_stated",
                evidence_refs=[],
                expires_at=None,
                created_at=datetime.now(UTC),
            )
            await memory.store(item)
            found = await memory.search("green tea")
            assert any(i.id == item.id for i in found)

    @pytest.mark.asyncio
    async def test_expired_memory_is_filtered(self, session_factory) -> None:
        async with session_factory() as session:
            memory = SqlAlchemyMemoryRepository(session)
            item = MemoryItem(
                id=MemoryId.generate(),
                content="temporary secret code 9911",
                source_turn_id=None,
                confidence="user_stated",
                evidence_refs=[],
                expires_at=datetime.now(UTC) - timedelta(hours=1),
                created_at=datetime.now(UTC),
            )
            await memory.store(item)
            found = await memory.search("secret code 9911")
            assert all(i.id != item.id for i in found)

    @pytest.mark.asyncio
    async def test_delete_memory(self, session_factory) -> None:
        async with session_factory() as session:
            memory = SqlAlchemyMemoryRepository(session)
            item = MemoryItem(
                id=MemoryId.generate(),
                content="forget me",
                source_turn_id=None,
                confidence="user_stated",
                evidence_refs=[],
                expires_at=None,
                created_at=datetime.now(UTC),
            )
            await memory.store(item)
            assert await memory.delete(item.id) is True
            assert all(i.id != item.id for i in await memory.list_all())


# ---------------------------------------------------------------------------
# Automations
# ---------------------------------------------------------------------------


class TestAutomations:
    @pytest.mark.asyncio
    async def test_due_once_automation_is_claimed_and_disabled(self, session_factory) -> None:
        async with session_factory() as session:
            automations = SqlAlchemyAutomationRepository(session)
            await automations.create(
                name="remind",
                command="notify me: stand up",
                schedule_kind="once",
                interval_seconds=None,
                next_run_at=datetime.now(UTC) - timedelta(seconds=5),
            )
            due = await automations.claim_due()
            assert len(due) == 1
            assert await automations.claim_due() == []
            stored = await automations.list_all()
            assert stored[0].enabled is False

    @pytest.mark.asyncio
    async def test_interval_automation_reschedules(self, session_factory) -> None:
        async with session_factory() as session:
            automations = SqlAlchemyAutomationRepository(session)
            await automations.create(
                name="poll",
                command="lights",
                schedule_kind="interval",
                interval_seconds=3600,
                next_run_at=datetime.now(UTC) - timedelta(seconds=5),
            )
            due = await automations.claim_due()
            assert len(due) == 1
            stored = await automations.list_all()
            assert stored[0].enabled is True
            assert stored[0].next_run_at is not None

    @pytest.mark.asyncio
    async def test_future_automation_not_claimed(self, session_factory) -> None:
        async with session_factory() as session:
            automations = SqlAlchemyAutomationRepository(session)
            await automations.create(
                name="later",
                command="lights",
                schedule_kind="once",
                interval_seconds=None,
                next_run_at=datetime.now(UTC) + timedelta(hours=1),
            )
            assert await automations.claim_due() == []
