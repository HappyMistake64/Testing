"""Pure domain models for the command-driven personal assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from fade_domain.ids import ApprovalId, AssistantSessionId, AssistantTurnId, MemoryId


class CommandMode(StrEnum):
    """User-selected execution mode."""

    ANSWER = "answer"
    DRAFT = "draft"
    EXECUTE = "execute"
    CONFIRM = "confirm"


class TurnState(StrEnum):
    """Durable lifecycle of an assistant command."""

    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Capability(StrEnum):
    """Explicit capability classes enforced before a tool can execute."""

    READ = "read"
    LOCAL_WRITE = "local_write"
    CODE_CHANGE = "code_change"
    NETWORK_READ = "network_read"
    NETWORK_WRITE = "network_write"
    DEVICE_CONTROL = "device_control"
    FINANCIAL = "financial"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class AssistantSession:
    id: AssistantSessionId
    title: str
    provider_id: str | None
    model_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AssistantTurn:
    id: AssistantTurnId
    session_id: AssistantSessionId
    command: str
    mode: CommandMode
    state: TurnState
    provider_id: str | None
    model_id: str | None
    response: str | None
    tool_calls: list[dict[str, object]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ToolApproval:
    id: ApprovalId
    turn_id: AssistantTurnId
    tool_name: str
    normalized_args_hash: str
    capability: Capability
    decision: str
    expires_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class MemoryItem:
    id: MemoryId
    content: str
    source_turn_id: AssistantTurnId | None
    confidence: str
    evidence_refs: list[str]
    expires_at: datetime | None
    created_at: datetime
