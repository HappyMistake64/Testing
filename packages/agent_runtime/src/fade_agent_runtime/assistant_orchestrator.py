"""Durable assistant turn orchestration.

Executes one user command end to end: deterministic intent compilation,
guarded tool execution, model answers with local memory context, evidence
recording, and approval-aware resumption.
"""

from __future__ import annotations

import json

from fade_domain.assistant import CommandMode, TurnState
from fade_domain.ids import AssistantTurnId, JobId
from fade_evidence.ledger import EvidenceLedger
from fade_infrastructure.assistant_repository import SqlAlchemyAssistantRepository
from fade_infrastructure.connectors import ConnectorError, ConnectorRegistry
from fade_infrastructure.evidence_repository import SqlAlchemyEvidenceRepository
from fade_infrastructure.memory_repository import SqlAlchemyMemoryRepository
from fade_infrastructure.settings import Settings
from fade_model_router.router import ModelRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fade_agent_runtime.assistant_intents import interpret
from fade_agent_runtime.assistant_tools import (
    ApprovalRequired,
    AssistantPaused,
    AssistantToolRegistry,
    ToolBudgetExceeded,
)

ASSISTANT_SYSTEM_PROMPT = (
    "You are FADE, a local personal assistant. Answer the user's question "
    "concisely using the provided verified memory context. Do not claim to "
    "have performed any action; you can only answer here."
)


class AssistantOrchestrator:
    """Execute assistant turns with policy, approvals and evidence."""

    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        model_router: ModelRouter,
        *,
        connectors: ConnectorRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._model_router = model_router
        self.connectors = connectors or ConnectorRegistry(settings)
        self._tools = AssistantToolRegistry(
            connectors=self.connectors,
            approval_ttl_seconds=settings.assistant_approval_ttl_seconds,
        )

    @property
    def tools(self) -> AssistantToolRegistry:
        return self._tools

    async def execute_turn(
        self,
        turn_id: AssistantTurnId,
        *,
        worker_id: str = "assistant",
    ) -> TurnState:
        async with self._session_factory() as session:
            repository = SqlAlchemyAssistantRepository(session)
            memory = SqlAlchemyMemoryRepository(session)
            evidence = SqlAlchemyEvidenceRepository(session)

            turn = await repository.get_turn(turn_id)
            if turn is None:
                msg = f"Turn not found: {turn_id}"
                raise ValueError(msg)
            if turn.state in {TurnState.COMPLETED, TurnState.FAILED, TurnState.CANCELLED}:
                return turn.state

            job_id_raw = await repository.get_turn_job_id(turn_id)
            job_id = JobId.from_string(job_id_raw) if job_id_raw else None

            if await repository.is_paused():
                await repository.update_turn(
                    turn_id,
                    state=TurnState.FAILED,
                    response="Assistant is paused by emergency stop.",
                )
                return TurnState.FAILED

            if not await repository.try_begin_turn(turn_id):
                # Another executor (inline API or worker) already owns this turn.
                current = await repository.get_turn(turn_id)
                return current.state if current else TurnState.FAILED
            await self._record(
                evidence, job_id, "ASSISTANT_TURN_STARTED",
                {"turn_id": str(turn_id), "command": turn.command[:200]},
                worker_id,
            )

            intent = interpret(turn.command)

            if intent.kind == "answer" or turn.mode == CommandMode.ANSWER:
                return await self._answer(
                    repository, evidence, memory, turn_id, turn, job_id, worker_id
                )

            if turn.mode == CommandMode.DRAFT:
                preview = json.dumps(intent.tool_calls, default=str, indent=2)
                await repository.update_turn(
                    turn_id,
                    state=TurnState.COMPLETED,
                    response=f"Draft only — proposed tool calls:\n{preview}",
                    tool_calls=intent.tool_calls,
                )
                await self._record(
                    evidence, job_id, "ASSISTANT_TURN_DRAFTED",
                    {"turn_id": str(turn_id), "tool_calls": intent.tool_calls},
                    worker_id,
                )
                return TurnState.COMPLETED

            return await self._execute_tools(
                repository, evidence, memory, turn_id, turn, intent.tool_calls, job_id, worker_id
            )

    async def _execute_tools(
        self,
        repository: SqlAlchemyAssistantRepository,
        evidence: SqlAlchemyEvidenceRepository,
        memory: SqlAlchemyMemoryRepository,
        turn_id: AssistantTurnId,
        turn,
        tool_calls: list[dict[str, object]],
        job_id: JobId | None,
        worker_id: str,
    ) -> TurnState:
        max_calls = self._settings.assistant_max_tool_calls_per_turn
        if len(tool_calls) > max_calls:
            raise ToolBudgetExceeded(f"Turn exceeds tool budget of {max_calls}")

        executed = list(turn.tool_calls)
        already_done = {
            json.dumps(c.get("call"), sort_keys=True, default=str)
            for c in executed
            if c.get("status") == "ok"
        }
        results: list[str] = []

        for call in tool_calls:
            key = json.dumps(call, sort_keys=True, default=str)
            if key in already_done:
                continue
            tool_name = str(call["tool"])
            args = dict(call.get("args", {}))
            try:
                result = await self._tools.execute(
                    tool_name=tool_name,
                    args=args,
                    turn_id=turn_id,
                    repository=repository,
                    memory=memory,
                )
            except ApprovalRequired as approval:
                executed.append({
                    "call": call,
                    "status": "awaiting_approval",
                    "approval_id": approval.approval_id,
                })
                await repository.update_turn(
                    turn_id,
                    state=TurnState.AWAITING_APPROVAL,
                    response=(
                        f"Approval required for {tool_name}. "
                        f"Approve request {approval.approval_id} to continue."
                    ),
                    tool_calls=executed,
                )
                await self._record(
                    evidence, job_id, "ASSISTANT_APPROVAL_REQUESTED",
                    {
                        "turn_id": str(turn_id),
                        "tool": tool_name,
                        "approval_id": approval.approval_id,
                    },
                    worker_id,
                )
                return TurnState.AWAITING_APPROVAL
            except AssistantPaused:
                await repository.update_turn(
                    turn_id,
                    state=TurnState.FAILED,
                    response="Assistant is paused by emergency stop.",
                    tool_calls=executed,
                )
                return TurnState.FAILED
            except (ConnectorError, ValueError) as exc:
                executed.append({"call": call, "status": "error", "error": str(exc)})
                await repository.update_turn(
                    turn_id,
                    state=TurnState.FAILED,
                    response=f"Tool {tool_name} failed: {exc}",
                    tool_calls=executed,
                )
                await self._record(
                    evidence, job_id, "ASSISTANT_TOOL_FAILED",
                    {"turn_id": str(turn_id), "tool": tool_name, "error": str(exc)},
                    worker_id,
                )
                return TurnState.FAILED

            executed.append({"call": call, "status": "ok", "result": result})
            results.append(_summarize(tool_name, result))
            await self._record(
                evidence, job_id, "ASSISTANT_TOOL_EXECUTED",
                {"turn_id": str(turn_id), "tool": tool_name, "result": result},
                worker_id,
            )

        response = "\n".join(results) if results else "Done."
        await repository.update_turn(
            turn_id,
            state=TurnState.COMPLETED,
            response=response,
            tool_calls=executed,
        )
        await self._record(
            evidence, job_id, "ASSISTANT_TURN_COMPLETED",
            {"turn_id": str(turn_id), "tools_executed": len(results)},
            worker_id,
        )
        return TurnState.COMPLETED

    async def _answer(
        self,
        repository: SqlAlchemyAssistantRepository,
        evidence: SqlAlchemyEvidenceRepository,
        memory: SqlAlchemyMemoryRepository,
        turn_id: AssistantTurnId,
        turn,
        job_id: JobId | None,
        worker_id: str,
    ) -> TurnState:
        memories = await memory.search(turn.command, limit=5)
        context_lines = [f"- {m.content}" for m in memories]
        context = "\n".join(context_lines) if context_lines else "(no stored memory matched)"
        prompt = f"Verified memory context:\n{context}\n\nUser: {turn.command}"

        try:
            completion = await self._model_router.complete(
                provider_id=turn.provider_id,
                model_id=turn.model_id,
                system_prompt=ASSISTANT_SYSTEM_PROMPT,
                user_prompt=prompt,
            )
        except Exception as exc:  # noqa: BLE001
            await repository.update_turn(
                turn_id,
                state=TurnState.FAILED,
                response=f"No model provider available: {exc}",
            )
            await self._record(
                evidence, job_id, "ASSISTANT_MODEL_UNAVAILABLE",
                {"turn_id": str(turn_id), "error": str(exc)},
                worker_id,
            )
            return TurnState.FAILED

        await repository.update_turn(
            turn_id,
            state=TurnState.COMPLETED,
            response=completion.content,
            provider_id=completion.provider_id,
            model_id=completion.model_id,
        )
        await self._record(
            evidence, job_id, "ASSISTANT_TURN_COMPLETED",
            {
                "turn_id": str(turn_id),
                "provider_id": completion.provider_id,
                "model_id": completion.model_id,
            },
            worker_id,
        )
        return TurnState.COMPLETED

    async def _record(
        self,
        evidence: SqlAlchemyEvidenceRepository,
        job_id: JobId | None,
        event_type: str,
        payload: dict[str, object],
        worker_id: str,
    ) -> None:
        if job_id is None:
            return
        events = await evidence.list_for_job(job_id)
        ledger = EvidenceLedger.from_events(events) if events else EvidenceLedger()
        event = ledger.append(
            event_type=event_type,
            payload=payload,
            project_id=None,
            job_id=job_id,
            actor_type="worker",
            actor_id=worker_id,
        )
        await evidence.append(event)


def _summarize(tool_name: str, result: dict[str, object]) -> str:
    if tool_name == "memory_store":
        return "Stored in memory."
    if tool_name == "memory_search":
        items = result.get("items", [])
        if not items:
            return "No matching memories."
        lines = [f"- {i['content']}" for i in items]  # type: ignore[index]
        return "I remember:\n" + "\n".join(lines)
    if tool_name == "calendar_list":
        events = result.get("events", [])
        if not events:
            return "No upcoming events."
        lines = [f"- {e['title']} at {e['start']}" for e in events]  # type: ignore[index]
        return "Upcoming events:\n" + "\n".join(lines)
    if tool_name == "calendar_create":
        return f"Event created: {result.get('title')}"
    if tool_name == "email_search":
        messages = result.get("messages", [])
        if not messages:
            return "No matching emails."
        lines = [f"- {m['subject']} ({m['sender']})" for m in messages]  # type: ignore[index]
        return "Emails:\n" + "\n".join(lines)
    if tool_name == "email_draft":
        return f"Draft created: {result.get('draft_id')} — say 'send email <id>' to send it."
    if tool_name == "email_send":
        return "Email sent."
    if tool_name == "notify_send":
        return "Notification delivered."
    if tool_name == "home_state":
        if "states" in result:
            lines = [
                f"- {s['entity_id']}: {s['state']}"
                for s in result["states"]  # type: ignore[union-attr]
            ]
            return "Device states:\n" + "\n".join(lines) if lines else "No devices."
        return f"{result.get('entity_id')}: {result.get('state')}"
    if tool_name == "home_control":
        return f"{result.get('entity_id')} is now {result.get('state')}."
    return json.dumps(result, default=str)
