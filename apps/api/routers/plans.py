"""Plans API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from apps.api.dependencies import get_goal_service, get_job_service, get_plan_service
from apps.api.routers.jobs import JobResponse, _to_job_response
from fade_application.jobs import CreateJobCommand, JobService
from fade_application.planning import GoalApplicationService, PlanApplicationService
from fade_domain.ids import GoalId, PlanId
from fade_domain.types import AutonomyLevel
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/plans", tags=["plans"])


class PlanStepResponse(BaseModel):
    ordinal: int
    title: str
    description: str
    step_type: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    id: str
    goal_id: str
    version: int
    status: str
    assumptions: list[str]
    steps: list[PlanStepResponse]
    test_plan: list[str]
    risk_level: str
    model_id: str | None
    created_at: datetime
    approved_at: datetime | None = None


class PlanListResponse(BaseModel):
    items: list[PlanResponse]
    total: int


def _to_plan_response(plan) -> PlanResponse:
    return PlanResponse(
        id=str(plan.id),
        goal_id=str(plan.goal_id),
        version=plan.version,
        status=plan.status.value,
        assumptions=plan.assumptions,
        steps=[
            PlanStepResponse(
                ordinal=s.ordinal,
                title=s.title,
                description=s.description,
                step_type=s.step_type,
                acceptance_criteria=s.acceptance_criteria,
            )
            for s in plan.steps
        ],
        test_plan=plan.test_plan,
        risk_level=plan.risk_level.value,
        model_id=plan.model_id,
        created_at=plan.created_at,
        approved_at=plan.approved_at,
    )


@router.post("", response_model=PlanResponse, status_code=201)
async def propose_plan(
    service: Annotated[PlanApplicationService, Depends(get_plan_service)],
    goal_id: str = Query(...),
) -> PlanResponse:
    plan = await service.propose_plan(GoalId.from_string(goal_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return _to_plan_response(plan)


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    service: Annotated[PlanApplicationService, Depends(get_plan_service)],
) -> PlanResponse:
    plan = await service.get_plan(PlanId.from_string(plan_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _to_plan_response(plan)


@router.get("", response_model=PlanListResponse)
async def list_plans(
    service: Annotated[PlanApplicationService, Depends(get_plan_service)],
    goal_id: str = Query(...),
) -> PlanListResponse:
    plans = await service.list_plans(GoalId.from_string(goal_id))
    items = [_to_plan_response(p) for p in plans]
    return PlanListResponse(items=items, total=len(items))


@router.post("/{plan_id}/approve", response_model=PlanResponse)
async def approve_plan(
    plan_id: str,
    service: Annotated[PlanApplicationService, Depends(get_plan_service)],
) -> PlanResponse:
    plan = await service.approve_plan(PlanId.from_string(plan_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _to_plan_response(plan)


@router.post("/{plan_id}/reject", response_model=PlanResponse)
async def reject_plan(
    plan_id: str,
    service: Annotated[PlanApplicationService, Depends(get_plan_service)],
) -> PlanResponse:
    plan = await service.reject_plan(PlanId.from_string(plan_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _to_plan_response(plan)


@router.post("/{plan_id}/jobs", response_model=JobResponse, status_code=201)
async def create_job_from_plan(
    plan_id: str,
    plan_service: Annotated[PlanApplicationService, Depends(get_plan_service)],
    goal_service: Annotated[GoalApplicationService, Depends(get_goal_service)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    plan = await plan_service.get_plan(PlanId.from_string(plan_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    goal = await goal_service.get_goal(plan.goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    job = await job_service.create_job(
        CreateJobCommand(
            project_id=goal.project_id,
            job_type="implementation",
            payload={"plan_id": str(plan.id), "goal_id": str(goal.id)},
            autonomy_level=AutonomyLevel.PLAN,
        )
    )
    return _to_job_response(job)
