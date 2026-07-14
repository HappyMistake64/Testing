"""Goal and plan application services."""

from __future__ import annotations

from fade_domain.goal import Goal
from fade_domain.ids import GoalId, PlanId, ProjectId
from fade_domain.plan import Plan, PlanStatus
from fade_planning.goal_service import CreateGoalCommand, GoalService
from fade_planning.plan_service import PlanService, ProposePlanCommand

from fade_application.ports import (
    GoalRepositoryPort,
    PlanRepositoryPort,
    ProjectAnalysisPort,
    ProjectRepositoryPort,
)


class GoalApplicationService:
    """Goal use cases with persistence."""

    def __init__(
        self,
        goals: GoalRepositoryPort,
        projects: ProjectRepositoryPort,
    ) -> None:
        self._goals = goals
        self._projects = projects

    async def create_goal(self, command: CreateGoalCommand) -> Goal | None:
        if await self._projects.get_by_id(command.project_id) is None:
            return None
        goal = GoalService.create(command)
        return await self._goals.create(goal)

    async def get_goal(self, goal_id: GoalId) -> Goal | None:
        return await self._goals.get_by_id(goal_id)

    async def list_goals(self, project_id: ProjectId) -> list[Goal]:
        return await self._goals.list_by_project(project_id)


class PlanApplicationService:
    """Plan use cases with model router."""

    def __init__(
        self,
        plans: PlanRepositoryPort,
        goals: GoalRepositoryPort,
        analysis: ProjectAnalysisPort,
        plan_service: PlanService,
    ) -> None:
        self._plans = plans
        self._goals = goals
        self._analysis = analysis
        self._plan_service = plan_service

    async def propose_plan(self, goal_id: GoalId) -> Plan | None:
        goal = await self._goals.get_by_id(goal_id)
        if goal is None:
            return None
        profile = await self._analysis.get_latest_profile(goal.project_id)
        existing = await self._plans.list_by_goal(goal_id)
        version = len(existing) + 1
        plan = await self._plan_service.propose_plan(
            ProposePlanCommand(goal=goal, profile=profile),
            version=version,
        )
        return await self._plans.create(plan)

    async def get_plan(self, plan_id: PlanId) -> Plan | None:
        return await self._plans.get_by_id(plan_id)

    async def list_plans(self, goal_id: GoalId) -> list[Plan]:
        return await self._plans.list_by_goal(goal_id)

    async def approve_plan(self, plan_id: PlanId) -> Plan | None:
        return await self._plans.update_status(plan_id, PlanStatus.APPROVED)

    async def reject_plan(self, plan_id: PlanId) -> Plan | None:
        return await self._plans.update_status(plan_id, PlanStatus.REJECTED)
