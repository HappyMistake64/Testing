"""Goal repository SQLAlchemy implementation."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fade_application.ports import GoalRepositoryPort
from fade_domain.goal import Goal, GoalStatus
from fade_domain.ids import GoalId, ProjectId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import GoalModel


class SqlAlchemyGoalRepository(GoalRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, goal: Goal) -> Goal:
        model = GoalModel(
            id=str(goal.id),
            project_id=str(goal.project_id),
            title=goal.title,
            intent=goal.intent,
            constraints_json=json.dumps(goal.constraints),
            priority=goal.priority,
            status=goal.status.value,
            metadata_json=json.dumps(goal.metadata),
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)

    async def get_by_id(self, goal_id: GoalId) -> Goal | None:
        result = await self._session.execute(
            select(GoalModel).where(GoalModel.id == str(goal_id))
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_by_project(self, project_id: ProjectId) -> list[Goal]:
        result = await self._session.execute(
            select(GoalModel)
            .where(GoalModel.project_id == str(project_id))
            .order_by(GoalModel.created_at.desc())
        )
        return [_to_domain(row) for row in result.scalars()]

    async def update(self, goal: Goal) -> Goal:
        result = await self._session.execute(
            select(GoalModel).where(GoalModel.id == str(goal.id))
        )
        model = result.scalar_one()
        model.title = goal.title
        model.intent = goal.intent
        model.constraints_json = json.dumps(goal.constraints)
        model.priority = goal.priority
        model.status = goal.status.value
        model.metadata_json = json.dumps(goal.metadata)
        model.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)


def _to_domain(model: GoalModel) -> Goal:
    return Goal(
        id=GoalId(model.id),
        project_id=ProjectId(model.project_id),
        title=model.title,
        intent=model.intent,
        constraints=json.loads(model.constraints_json),
        priority=model.priority,
        status=GoalStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
        metadata=json.loads(model.metadata_json),
    )
