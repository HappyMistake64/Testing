"""Goals API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from apps.api.dependencies import get_goal_service
from fade_application.planning import GoalApplicationService
from fade_domain.ids import GoalId, ProjectId
from fade_planning.goal_service import CreateGoalCommand
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/goals", tags=["goals"])


class CreateGoalRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=512)
    intent: str = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    priority: int = 0


class GoalResponse(BaseModel):
    id: str
    project_id: str
    title: str
    intent: str
    constraints: list[str]
    priority: int
    status: str
    created_at: datetime
    updated_at: datetime


class GoalListResponse(BaseModel):
    items: list[GoalResponse]
    total: int


def _to_goal_response(goal) -> GoalResponse:
    return GoalResponse(
        id=str(goal.id),
        project_id=str(goal.project_id),
        title=goal.title,
        intent=goal.intent,
        constraints=goal.constraints,
        priority=goal.priority,
        status=goal.status.value,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


@router.post("", response_model=GoalResponse, status_code=201)
async def create_goal(
    body: CreateGoalRequest,
    service: Annotated[GoalApplicationService, Depends(get_goal_service)],
) -> GoalResponse:
    goal = await service.create_goal(
        CreateGoalCommand(
            project_id=ProjectId.from_string(body.project_id),
            title=body.title,
            intent=body.intent,
            constraints=body.constraints,
            priority=body.priority,
        )
    )
    if goal is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_goal_response(goal)


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    service: Annotated[GoalApplicationService, Depends(get_goal_service)],
) -> GoalResponse:
    goal = await service.get_goal(GoalId.from_string(goal_id))
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return _to_goal_response(goal)


@router.get("", response_model=GoalListResponse)
async def list_goals(
    service: Annotated[GoalApplicationService, Depends(get_goal_service)],
    project_id: str = Query(...),
) -> GoalListResponse:
    goals = await service.list_goals(ProjectId.from_string(project_id))
    items = [_to_goal_response(g) for g in goals]
    return GoalListResponse(items=items, total=len(items))
