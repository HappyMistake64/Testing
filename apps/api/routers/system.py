"""System API routes."""

from __future__ import annotations

from typing import Annotated, Any

from apps.api.dependencies import get_health_service
from fade_infrastructure.system_health import SystemHealthService
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/system", tags=["system"])


class DatabaseHealthResponse(BaseModel):
    connected: bool
    engine: str
    wal_mode: bool | None = None
    integrity_ok: bool | None = None
    project_count: int | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: DatabaseHealthResponse
    capabilities: dict[str, bool]


class DoctorIssue(BaseModel):
    severity: str
    code: str
    message: str


class DoctorResponse(BaseModel):
    status: str
    version: str
    environment: str
    settings: dict[str, Any]
    checks: dict[str, Any]
    issues: list[DoctorIssue]
    capabilities: dict[str, bool]
    model_providers: list[dict[str, Any]] = []


@router.get("/health", response_model=HealthResponse)
async def health(
    service: Annotated[SystemHealthService, Depends(get_health_service)],
) -> HealthResponse:
    snapshot = await service.check_health()
    return HealthResponse(
        status=snapshot.status,
        version=snapshot.version,
        environment=snapshot.environment,
        database=DatabaseHealthResponse(
            connected=snapshot.database.connected,
            engine=snapshot.database.engine,
            wal_mode=snapshot.database.wal_mode,
            integrity_ok=snapshot.database.integrity_ok,
            project_count=snapshot.database.project_count,
        ),
        capabilities=snapshot.capabilities,
    )


@router.get("/doctor", response_model=DoctorResponse)
async def doctor(
    service: Annotated[SystemHealthService, Depends(get_health_service)],
) -> DoctorResponse:
    result = await service.check_doctor()
    return DoctorResponse(**result)
