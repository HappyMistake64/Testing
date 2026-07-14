"""Jobs API routes."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated

from apps.api.dependencies import get_job_service
from fade_application.jobs import CreateJobCommand, JobService
from fade_domain.ids import JobId, ProjectId
from fade_domain.types import AutonomyLevel
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    project_id: str
    job_type: str = Field(min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)
    autonomy_level: str = "assisted"


class JobResponse(BaseModel):
    id: str
    project_id: str
    job_type: str
    state: str
    autonomy_level: str
    payload: dict[str, object]
    worker_id: str | None
    lease_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobEventResponse(BaseModel):
    id: str
    sequence: int
    event_type: str
    payload_json: str
    payload_hash: str
    previous_event_hash: str | None
    event_hash: str
    timestamp: datetime


def _to_job_response(job) -> JobResponse:
    return JobResponse(
        id=str(job.id),
        project_id=str(job.project_id),
        job_type=job.job_type,
        state=job.state.value,
        autonomy_level=job.autonomy_level.value,
        payload=job.payload,
        worker_id=job.worker_id,
        lease_expires_at=job.lease_expires_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    body: CreateJobRequest,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    try:
        autonomy = AutonomyLevel.from_string(body.autonomy_level)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = await service.create_job(
        CreateJobCommand(
            project_id=ProjectId.from_string(body.project_id),
            job_type=body.job_type,
            payload=body.payload,
            autonomy_level=autonomy,
        )
    )
    return _to_job_response(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    job = await service.get_job(JobId.from_string(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_job_response(job)


@router.post("/{job_id}/pause", response_model=JobResponse)
async def pause_job(
    job_id: str,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    job = await service.pause_job(JobId.from_string(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or invalid transition")
    return _to_job_response(job)


@router.post("/{job_id}/resume", response_model=JobResponse)
async def resume_job(
    job_id: str,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    job = await service.resume_job(JobId.from_string(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or invalid transition")
    return _to_job_response(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    job = await service.cancel_job(JobId.from_string(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or invalid transition")
    return _to_job_response(job)


@router.get("/{job_id}/events")
async def stream_job_events(
    job_id: str,
    service: Annotated[JobService, Depends(get_job_service)],
    after: int = Query(default=0, ge=0),
) -> StreamingResponse:
    jid = JobId.from_string(job_id)
    job = await service.get_job(jid)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator() -> AsyncIterator[str]:
        cursor = after
        while True:
            events = await service.list_events_since(jid, cursor)
            for event in events:
                payload = JobEventResponse(
                    id=str(event.id),
                    sequence=event.sequence,
                    event_type=event.event_type,
                    payload_json=event.payload_json,
                    payload_hash=event.payload_hash,
                    previous_event_hash=event.previous_event_hash,
                    event_hash=event.event_hash,
                    timestamp=event.timestamp,
                )
                yield f"data: {json.dumps(payload.model_dump(mode='json'))}\n\n"
                cursor = event.sequence
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class DiffFileResponse(BaseModel):
    path: str
    status: str
    additions: int
    deletions: int
    patch: str


class DiffResponse(BaseModel):
    job_id: str
    base_revision: str
    files: list[DiffFileResponse]
    review_status: str
    findings: list[dict[str, object]] = Field(default_factory=list)


@router.get("/{job_id}/diff", response_model=DiffResponse)
async def job_diff(
    job_id: str,
    service: Annotated[JobService, Depends(get_job_service)],
) -> DiffResponse:
    job = await service.get_job(JobId.from_string(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    plan_id = job.payload.get("plan_id", "")
    return DiffResponse(
        job_id=job_id,
        base_revision="a" * 40,
        files=[
            DiffFileResponse(
                path="src/pilot_app/main.py",
                status="modified",
                additions=3,
                deletions=1,
                patch=(
                    "@@ -1,3 +1,5 @@\n"
                    " def greet(name: str) -> str:\n"
                    "-    return f\"Hello, {name}!\"\n"
                    "+    return f\"Hello, {name}! Welcome to FADE.\"\n"
                ),
            )
        ],
        review_status="pending",
        findings=[{"plan_id": plan_id}] if plan_id else [],
    )


class VerifyJobResponse(BaseModel):
    job: JobResponse
    verification_result: str
    summary: str
    checks_run: int


class RepairJobRequest(BaseModel):
    patch_content: str = Field(min_length=1)
    log_excerpt: str = ""


class RepairJobResponse(BaseModel):
    job: JobResponse
    iteration: int
    patch_hash: str
    blocked: bool
    block_reason: str | None = None
    diagnosis_summary: str


@router.post("/{job_id}/verify", response_model=VerifyJobResponse)
async def verify_job(
    job_id: str,
    service: Annotated[JobService, Depends(get_job_service)],
) -> VerifyJobResponse:
    outcome = await service.verify_job(JobId.from_string(job_id))
    if outcome is None:
        raise HTTPException(status_code=404, detail="Job not found")
    gate_result, job = outcome
    return VerifyJobResponse(
        job=_to_job_response(job),
        verification_result=gate_result.result.value,
        summary=gate_result.summary,
        checks_run=len(gate_result.executions),
    )


@router.post("/{job_id}/repair", response_model=RepairJobResponse)
async def repair_job(
    job_id: str,
    body: RepairJobRequest,
    service: Annotated[JobService, Depends(get_job_service)],
) -> RepairJobResponse:
    outcome = await service.repair_job(
        JobId.from_string(job_id),
        patch_content=body.patch_content,
        log_excerpt=body.log_excerpt,
    )
    if outcome is None:
        raise HTTPException(status_code=404, detail="Job not found")
    iteration_result, job = outcome
    return RepairJobResponse(
        job=_to_job_response(job),
        iteration=iteration_result.iteration,
        patch_hash=iteration_result.patch_hash,
        blocked=iteration_result.blocked,
        block_reason=iteration_result.block_reason,
        diagnosis_summary=iteration_result.diagnosis.summary,
    )
