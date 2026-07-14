"""Plan repository SQLAlchemy implementation."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fade_application.ports import PlanRepositoryPort
from fade_domain.ids import GoalId, PlanId
from fade_domain.plan import Plan, PlanStatus, PlanStep
from fade_domain.types import RiskLevel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import ApprovalModel, PlanModel


class SqlAlchemyPlanRepository(PlanRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, plan: Plan) -> Plan:
        model = PlanModel(
            id=str(plan.id),
            goal_id=str(plan.goal_id),
            version=plan.version,
            status=plan.status.value,
            plan_json=_serialize_plan(plan),
            model_id=plan.model_id,
            created_at=plan.created_at,
            approved_at=plan.approved_at,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)

    async def get_by_id(self, plan_id: PlanId) -> Plan | None:
        result = await self._session.execute(
            select(PlanModel).where(PlanModel.id == str(plan_id))
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_by_goal(self, goal_id: GoalId) -> list[Plan]:
        result = await self._session.execute(
            select(PlanModel)
            .where(PlanModel.goal_id == str(goal_id))
            .order_by(PlanModel.version.desc())
        )
        return [_to_domain(row) for row in result.scalars()]

    async def update_status(self, plan_id: PlanId, status: PlanStatus) -> Plan | None:
        result = await self._session.execute(
            select(PlanModel).where(PlanModel.id == str(plan_id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.status = status.value
        if status == PlanStatus.APPROVED:
            model.approved_at = datetime.now(UTC)
            self._session.add(
                ApprovalModel(
                    id=str(PlanId.generate()),
                    subject_type="plan",
                    subject_id=str(plan_id),
                    decision="approved",
                    reason=None,
                    actor="system",
                )
            )
        elif status == PlanStatus.REJECTED:
            self._session.add(
                ApprovalModel(
                    id=str(PlanId.generate()),
                    subject_type="plan",
                    subject_id=str(plan_id),
                    decision="rejected",
                    reason=None,
                    actor="system",
                )
            )
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)


def _serialize_plan(plan: Plan) -> str:
    data = {
        "assumptions": plan.assumptions,
        "steps": [
            {
                "ordinal": s.ordinal,
                "title": s.title,
                "description": s.description,
                "step_type": s.step_type,
                "acceptance_criteria": s.acceptance_criteria,
            }
            for s in plan.steps
        ],
        "test_plan": plan.test_plan,
        "risk_level": plan.risk_level.value,
        "raw_output": plan.raw_output,
    }
    return json.dumps(data)


def _to_domain(model: PlanModel) -> Plan:
    data = json.loads(model.plan_json)
    steps = [
        PlanStep(
            ordinal=s["ordinal"],
            title=s["title"],
            description=s["description"],
            step_type=s["step_type"],
            acceptance_criteria=s.get("acceptance_criteria", []),
        )
        for s in data.get("steps", [])
    ]
    return Plan(
        id=PlanId(model.id),
        goal_id=GoalId(model.goal_id),
        version=model.version,
        status=PlanStatus(model.status),
        assumptions=data.get("assumptions", []),
        steps=steps,
        test_plan=data.get("test_plan", []),
        risk_level=RiskLevel(data.get("risk_level", "medium")),
        created_at=model.created_at,
        approved_at=model.approved_at,
        model_id=model.model_id,
        raw_output=data.get("raw_output"),
    )
