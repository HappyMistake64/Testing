"""Typed assistant tool registry with capability classes and approval binding.

Every tool call is bound to an originating user turn. Read-class tools run
immediately; mutating capabilities require a granted approval that matches the
exact tool name and normalized arguments hash.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from fade_domain.assistant import Capability, MemoryItem, ToolApproval
from fade_domain.ids import ApprovalId, AssistantTurnId, MemoryId
from fade_infrastructure.assistant_repository import SqlAlchemyAssistantRepository
from fade_infrastructure.connectors import ConnectorRegistry, upcoming_window
from fade_infrastructure.memory_repository import SqlAlchemyMemoryRepository

READ_CAPABILITIES = frozenset({Capability.READ, Capability.NETWORK_READ})


class ApprovalRequired(Exception):
    """Raised when a mutating tool call needs explicit user approval."""

    def __init__(self, approval_id: str, tool_name: str, args_preview: str) -> None:
        self.approval_id = approval_id
        self.tool_name = tool_name
        self.args_preview = args_preview
        super().__init__(f"Approval required for {tool_name}")


class AssistantPaused(Exception):
    """Raised when the emergency stop is active."""


class ToolBudgetExceeded(Exception):
    """Raised when the per-turn tool budget is exhausted."""


def normalize_args_hash(tool_name: str, args: dict[str, object]) -> str:
    canonical = json.dumps({"tool": tool_name, "args": args}, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    capability: Capability
    description: str
    handler: Callable[..., Awaitable[dict[str, object]]]
    arg_names: frozenset[str] = field(default_factory=frozenset)


class AssistantToolRegistry:
    """Registry and guarded executor for assistant tools."""

    def __init__(
        self,
        *,
        connectors: ConnectorRegistry,
        approval_ttl_seconds: int = 900,
    ) -> None:
        self._connectors = connectors
        self._approval_ttl_seconds = approval_ttl_seconds
        self._tools: dict[str, ToolSpec] = {}
        self._register_builtin()

    def list_specs(self) -> list[dict[str, object]]:
        return [
            {
                "name": spec.name,
                "capability": spec.capability.value,
                "description": spec.description,
                "requires_approval": spec.capability not in READ_CAPABILITIES,
            }
            for spec in self._tools.values()
        ]

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    async def execute(
        self,
        *,
        tool_name: str,
        args: dict[str, object],
        turn_id: AssistantTurnId,
        repository: SqlAlchemyAssistantRepository,
        memory: SqlAlchemyMemoryRepository,
    ) -> dict[str, object]:
        """Execute one tool call under policy, approval and pause checks."""
        if await repository.is_paused():
            raise AssistantPaused("Assistant side effects are paused by emergency stop")

        spec = self._tools.get(tool_name)
        if spec is None:
            msg = f"Unknown tool: {tool_name}"
            raise ValueError(msg)

        unknown = set(args) - set(spec.arg_names)
        if unknown:
            msg = f"Unexpected arguments for {tool_name}: {sorted(unknown)}"
            raise ValueError(msg)

        if spec.capability not in READ_CAPABILITIES:
            args_hash = normalize_args_hash(tool_name, args)
            granted = await repository.find_granted_approval(
                turn_id=turn_id,
                tool_name=tool_name,
                normalized_args_hash=args_hash,
            )
            if granted is None:
                approval = ToolApproval(
                    id=ApprovalId.generate(),
                    turn_id=turn_id,
                    tool_name=tool_name,
                    normalized_args_hash=args_hash,
                    capability=spec.capability,
                    decision="pending",
                    expires_at=datetime.now(UTC)
                    + timedelta(seconds=self._approval_ttl_seconds),
                    created_at=datetime.now(UTC),
                )
                preview = json.dumps(args, default=str)[:500]
                await repository.create_approval(approval, args_preview=preview)
                raise ApprovalRequired(str(approval.id), tool_name, preview)
            await repository.consume_approval(granted.id)

        return await spec.handler(args=args, memory=memory, turn_id=turn_id)

    # ------------------------------------------------------------------
    # Built-in tools
    # ------------------------------------------------------------------

    def _register_builtin(self) -> None:
        connectors = self._connectors

        async def memory_store(*, args, memory, turn_id):
            item = MemoryItem(
                id=MemoryId.generate(),
                content=str(args["content"]),
                source_turn_id=turn_id,
                confidence="user_stated",
                evidence_refs=[],
                expires_at=None,
                created_at=datetime.now(UTC),
            )
            await memory.store(item)
            return {"memory_id": str(item.id), "stored": True}

        async def memory_search(*, args, memory, turn_id):
            items = await memory.search(str(args["query"]), limit=int(args.get("limit", 5)))
            return {
                "items": [
                    {"id": str(i.id), "content": i.content, "confidence": i.confidence}
                    for i in items
                ]
            }

        async def calendar_list(*, args, memory, turn_id):
            start, end = upcoming_window(int(args.get("days", 1)))
            events = await connectors.calendar.list_events(start=start, end=end)
            return {
                "events": [
                    {
                        "id": e.id,
                        "title": e.title,
                        "start": e.start.isoformat(),
                        "end": e.end.isoformat() if e.end else None,
                    }
                    for e in events
                ]
            }

        async def calendar_create(*, args, memory, turn_id):
            start = datetime.fromisoformat(str(args["start"]))
            end = datetime.fromisoformat(str(args["end"])) if args.get("end") else None
            event = await connectors.calendar.create_event(
                title=str(args["title"]), start=start, end=end
            )
            return {"event_id": event.id, "title": event.title, "created": True}

        async def email_search(*, args, memory, turn_id):
            messages = await connectors.email.search(
                str(args["query"]), limit=int(args.get("limit", 10))
            )
            return {
                "messages": [
                    {"id": m.id, "subject": m.subject, "sender": m.sender, "sent": m.sent}
                    for m in messages
                ]
            }

        async def email_draft(*, args, memory, turn_id):
            draft = await connectors.email.draft(
                to=str(args["to"]),
                subject=str(args["subject"]),
                body=str(args["body"]),
            )
            return {"draft_id": draft.id, "subject": draft.subject, "sent": False}

        async def email_send(*, args, memory, turn_id):
            sent = await connectors.email.send(str(args["draft_id"]))
            return {"message_id": sent.id, "sent": sent.sent}

        async def notify_send(*, args, memory, turn_id):
            notification_id = await connectors.notifications.notify(
                title=str(args.get("title", "FADE")),
                message=str(args["message"]),
            )
            return {"notification_id": notification_id, "delivered": True}

        async def home_state(*, args, memory, turn_id):
            entity_id = args.get("entity_id")
            if entity_id:
                state = await connectors.smart_home.get_state(str(entity_id))
                return {"entity_id": state.entity_id, "state": state.state}
            states = await connectors.smart_home.list_states(
                domain=str(args["domain"]) if args.get("domain") else None
            )
            return {
                "states": [{"entity_id": s.entity_id, "state": s.state} for s in states]
            }

        async def home_control(*, args, memory, turn_id):
            entity_id = str(args["entity_id"])
            service = str(args["service"])
            if service not in {"turn_on", "turn_off", "toggle"}:
                msg = f"Service not allowed: {service}"
                raise ValueError(msg)
            domain = entity_id.split(".", 1)[0]
            state = await connectors.smart_home.call_service(
                domain=domain, service=service, entity_id=entity_id
            )
            return {"entity_id": state.entity_id, "state": state.state}

        self._tools = {
            "memory_store": ToolSpec(
                name="memory_store",
                capability=Capability.READ,
                description="Store a user-stated fact in local durable memory",
                handler=memory_store,
                arg_names=frozenset({"content"}),
            ),
            "memory_search": ToolSpec(
                name="memory_search",
                capability=Capability.READ,
                description="Search local durable memory",
                handler=memory_search,
                arg_names=frozenset({"query", "limit"}),
            ),
            "calendar_list": ToolSpec(
                name="calendar_list",
                capability=Capability.NETWORK_READ,
                description="List upcoming calendar events",
                handler=calendar_list,
                arg_names=frozenset({"days"}),
            ),
            "calendar_create": ToolSpec(
                name="calendar_create",
                capability=Capability.NETWORK_WRITE,
                description="Create a calendar event",
                handler=calendar_create,
                arg_names=frozenset({"title", "start", "end"}),
            ),
            "email_search": ToolSpec(
                name="email_search",
                capability=Capability.NETWORK_READ,
                description="Search email messages",
                handler=email_search,
                arg_names=frozenset({"query", "limit"}),
            ),
            "email_draft": ToolSpec(
                name="email_draft",
                capability=Capability.READ,
                description="Create an email draft without sending",
                handler=email_draft,
                arg_names=frozenset({"to", "subject", "body"}),
            ),
            "email_send": ToolSpec(
                name="email_send",
                capability=Capability.NETWORK_WRITE,
                description="Send a previously drafted email",
                handler=email_send,
                arg_names=frozenset({"draft_id"}),
            ),
            "notify_send": ToolSpec(
                name="notify_send",
                capability=Capability.NETWORK_READ,
                description="Send an owner notification",
                handler=notify_send,
                arg_names=frozenset({"title", "message"}),
            ),
            "home_state": ToolSpec(
                name="home_state",
                capability=Capability.NETWORK_READ,
                description="Read smart-home entity states",
                handler=home_state,
                arg_names=frozenset({"entity_id", "domain"}),
            ),
            "home_control": ToolSpec(
                name="home_control",
                capability=Capability.DEVICE_CONTROL,
                description="Control an allowlisted smart-home entity",
                handler=home_control,
                arg_names=frozenset({"entity_id", "service"}),
            ),
        }
