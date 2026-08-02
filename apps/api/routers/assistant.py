"""Personal assistant API routes: sessions, turns, approvals, memory, voice."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from apps.api.dependencies import get_assistant_runtime, get_assistant_service
from fade_agent_runtime.assistant_orchestrator import AssistantOrchestrator
from fade_application.assistant import AssistantService
from fade_domain.assistant import CommandMode
from fade_domain.ids import ApprovalId, AssistantSessionId, AssistantTurnId, MemoryId
from fade_infrastructure.connectors import ConnectorError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/assistant", tags=["assistant"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SessionResponse(BaseModel):
    id: str
    title: str
    provider_id: str | None
    model_id: str | None
    created_at: datetime | None = None


class CreateSessionRequest(BaseModel):
    title: str = ""
    provider_id: str | None = None
    model_id: str | None = None


class TurnResponse(BaseModel):
    id: str
    session_id: str
    command: str
    mode: str
    state: str
    provider_id: str | None
    model_id: str | None
    response: str | None
    tool_calls: list[dict[str, Any]]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CreateTurnRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4000)
    mode: str = "execute"
    provider_id: str | None = None
    model_id: str | None = None


class ApprovalResponse(BaseModel):
    id: str
    turn_id: str
    tool_name: str
    capability: str
    args_preview: str
    created_at: datetime | None = None


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    turn_id: str
    decision: str
    turn_requeued: bool


class MemoryResponse(BaseModel):
    id: str
    content: str
    confidence: str
    created_at: datetime | None = None


class StoreMemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class AutomationResponse(BaseModel):
    id: str
    name: str
    command: str
    schedule_kind: str
    interval_seconds: int | None
    next_run_at: datetime | None
    enabled: bool
    last_run_at: datetime | None


class CreateAutomationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    command: str = Field(min_length=1, max_length=4000)
    schedule_kind: str = "once"
    interval_seconds: int | None = None
    delay_seconds: int | None = None


class EmergencyStopRequest(BaseModel):
    paused: bool
    reason: str | None = None


class TranscribeRequest(BaseModel):
    audio_b64: str | None = None
    text_hint: str | None = None


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class DescribeImageRequest(BaseModel):
    image_b64: str = Field(min_length=1)
    prompt: str | None = None


# ---------------------------------------------------------------------------
# Status and controls
# ---------------------------------------------------------------------------


@router.get("/status")
async def assistant_status(
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    runtime: Annotated[AssistantOrchestrator, Depends(get_assistant_runtime)],
) -> dict[str, Any]:
    return {
        "paused": await service.is_paused(),
        "tools": runtime.tools.list_specs(),
        "connectors": runtime.connectors.status(),
    }


@router.post("/emergency-stop")
async def emergency_stop(
    request: EmergencyStopRequest,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> dict[str, Any]:
    return await service.emergency_stop(paused=request.paused, reason=request.reason)


# ---------------------------------------------------------------------------
# Sessions and turns
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> SessionResponse:
    session = await service.create_session(
        title=request.title,
        provider_id=request.provider_id,
        model_id=request.model_id,
    )
    return _session_response(session)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> list[SessionResponse]:
    return [_session_response(s) for s in await service.list_sessions()]


@router.get("/sessions/{session_id}/turns", response_model=list[TurnResponse])
async def list_turns(
    session_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> list[TurnResponse]:
    turns = await service.list_turns(AssistantSessionId.from_string(session_id))
    return [_turn_response(t) for t in turns]


@router.post("/sessions/{session_id}/turns", response_model=TurnResponse, status_code=201)
async def create_turn(
    session_id: str,
    request: CreateTurnRequest,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> TurnResponse:
    try:
        mode = CommandMode(request.mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid mode: {request.mode}") from exc
    try:
        turn = await service.create_turn(
            AssistantSessionId.from_string(session_id),
            command=request.command,
            mode=mode,
            provider_id=request.provider_id,
            model_id=request.model_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _turn_response(turn)


@router.get("/turns/{turn_id}", response_model=TurnResponse)
async def get_turn(
    turn_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> TurnResponse:
    turn = await service.get_turn(AssistantTurnId.from_string(turn_id))
    if turn is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    return _turn_response(turn)


@router.post("/turns/{turn_id}/execute", response_model=TurnResponse)
async def execute_turn(
    turn_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    runtime: Annotated[AssistantOrchestrator, Depends(get_assistant_runtime)],
) -> TurnResponse:
    """Execute a queued turn inline (used when no worker is running)."""
    parsed = AssistantTurnId.from_string(turn_id)
    turn = await service.get_turn(parsed)
    if turn is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    await runtime.execute_turn(parsed, worker_id="api-inline")
    refreshed = await service.get_turn(parsed)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    return _turn_response(refreshed)


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


@router.get("/approvals", response_model=list[ApprovalResponse])
async def list_approvals(
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> list[ApprovalResponse]:
    pending = await service.list_pending_approvals()
    return [
        ApprovalResponse(
            id=str(p["id"]),
            turn_id=str(p["turn_id"]),
            tool_name=str(p["tool_name"]),
            capability=str(p["capability"]),
            args_preview=str(p["args_preview"]),
            created_at=p.get("created_at"),  # type: ignore[arg-type]
        )
        for p in pending
    ]


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalDecisionResponse)
async def approve(
    approval_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> ApprovalDecisionResponse:
    result = await service.decide_approval(ApprovalId.from_string(approval_id), approve=True)
    if result is None:
        raise HTTPException(status_code=404, detail="Approval not found or already decided")
    return ApprovalDecisionResponse(**result)  # type: ignore[arg-type]


@router.post("/approvals/{approval_id}/deny", response_model=ApprovalDecisionResponse)
async def deny(
    approval_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> ApprovalDecisionResponse:
    result = await service.decide_approval(ApprovalId.from_string(approval_id), approve=False)
    if result is None:
        raise HTTPException(status_code=404, detail="Approval not found or already decided")
    return ApprovalDecisionResponse(**result)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


@router.get("/memory", response_model=list[MemoryResponse])
async def list_memory(
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    query: str | None = None,
) -> list[MemoryResponse]:
    items = await (service.search_memory(query) if query else service.list_memory())
    return [
        MemoryResponse(
            id=str(i.id), content=i.content, confidence=i.confidence, created_at=i.created_at
        )
        for i in items
    ]


@router.post("/memory", response_model=MemoryResponse, status_code=201)
async def store_memory(
    request: StoreMemoryRequest,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> MemoryResponse:
    item = await service.store_memory(request.content)
    return MemoryResponse(
        id=str(item.id),
        content=item.content,
        confidence=item.confidence,
        created_at=item.created_at,
    )


@router.delete("/memory/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> None:
    deleted = await service.delete_memory(MemoryId.from_string(memory_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")


# ---------------------------------------------------------------------------
# Automations
# ---------------------------------------------------------------------------


@router.get("/automations", response_model=list[AutomationResponse])
async def list_automations(
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> list[AutomationResponse]:
    return [_automation_response(a) for a in await service.list_automations()]


@router.post("/automations", response_model=AutomationResponse, status_code=201)
async def create_automation(
    request: CreateAutomationRequest,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AutomationResponse:
    try:
        automation = await service.create_automation(
            name=request.name,
            command=request.command,
            schedule_kind=request.schedule_kind,
            interval_seconds=request.interval_seconds,
            delay_seconds=request.delay_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _automation_response(automation)


@router.post("/automations/{automation_id}/toggle", response_model=AutomationResponse)
async def toggle_automation(
    automation_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AutomationResponse:
    automations = {a.id: a for a in await service.list_automations()}
    current = automations.get(automation_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Automation not found")
    updated = await service.set_automation_enabled(automation_id, not current.enabled)
    if updated is None:
        raise HTTPException(status_code=404, detail="Automation not found")
    return _automation_response(updated)


@router.delete("/automations/{automation_id}", status_code=204)
async def delete_automation(
    automation_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> None:
    deleted = await service.delete_automation(automation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Automation not found")


# ---------------------------------------------------------------------------
# Voice and vision
# ---------------------------------------------------------------------------


@router.post("/voice/transcribe")
async def transcribe(
    request: TranscribeRequest,
    runtime: Annotated[AssistantOrchestrator, Depends(get_assistant_runtime)],
) -> dict[str, Any]:
    try:
        result = await runtime.connectors.speech_to_text.transcribe(
            audio_b64=request.audio_b64, text_hint=request.text_hint
        )
    except ConnectorError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    return {"text": result.text, "provider_id": result.provider_id}


@router.post("/voice/speak")
async def speak(
    request: SpeakRequest,
    runtime: Annotated[AssistantOrchestrator, Depends(get_assistant_runtime)],
) -> dict[str, Any]:
    result = await runtime.connectors.text_to_speech.speak(request.text)
    return {
        "text": result.text,
        "provider_id": result.provider_id,
        "audio_b64": result.audio_b64,
        "media_type": result.media_type,
    }


@router.post("/vision/describe")
async def describe_image(
    request: DescribeImageRequest,
    runtime: Annotated[AssistantOrchestrator, Depends(get_assistant_runtime)],
) -> dict[str, Any]:
    result = await runtime.connectors.vision.describe(
        image_b64=request.image_b64, prompt=request.prompt
    )
    return {"description": result.description, "provider_id": result.provider_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_response(session) -> SessionResponse:
    return SessionResponse(
        id=str(session.id),
        title=session.title,
        provider_id=session.provider_id,
        model_id=session.model_id,
        created_at=session.created_at,
    )


def _turn_response(turn) -> TurnResponse:
    return TurnResponse(
        id=str(turn.id),
        session_id=str(turn.session_id),
        command=turn.command,
        mode=turn.mode.value,
        state=turn.state.value,
        provider_id=turn.provider_id,
        model_id=turn.model_id,
        response=turn.response,
        tool_calls=turn.tool_calls,
        created_at=turn.created_at,
        updated_at=turn.updated_at,
    )


def _automation_response(automation) -> AutomationResponse:
    return AutomationResponse(
        id=automation.id,
        name=automation.name,
        command=automation.command,
        schedule_kind=automation.schedule_kind,
        interval_seconds=automation.interval_seconds,
        next_run_at=automation.next_run_at,
        enabled=automation.enabled,
        last_run_at=automation.last_run_at,
    )
