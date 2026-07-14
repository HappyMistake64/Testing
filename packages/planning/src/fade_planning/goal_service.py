"""Goal service helpers."""

from __future__ import annotations

from dataclasses import dataclass

from fade_domain.goal import Goal, GoalStatus
from fade_domain.ids import GoalId, ProjectId


@dataclass(frozen=True, slots=True)
class CreateGoalCommand:
    project_id: ProjectId
    title: str
    intent: str
    constraints: list[str] | None = None
    priority: int = 0


class GoalService:
    """Domain logic for goal creation and status transitions."""

    @staticmethod
    def create(command: CreateGoalCommand) -> Goal:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        return Goal(
            id=GoalId.generate(),
            project_id=command.project_id,
            title=command.title,
            intent=command.intent,
            constraints=command.constraints or [],
            priority=command.priority,
            status=GoalStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def activate(goal: Goal) -> Goal:
        return _with_status(goal, GoalStatus.ACTIVE)

    @staticmethod
    def complete(goal: Goal) -> Goal:
        return _with_status(goal, GoalStatus.COMPLETED)

    @staticmethod
    def cancel(goal: Goal) -> Goal:
        return _with_status(goal, GoalStatus.CANCELLED)


def _with_status(goal: Goal, status: GoalStatus) -> Goal:
    from datetime import UTC, datetime

    return Goal(
        id=goal.id,
        project_id=goal.project_id,
        title=goal.title,
        intent=goal.intent,
        constraints=goal.constraints,
        priority=goal.priority,
        status=status,
        created_at=goal.created_at,
        updated_at=datetime.now(UTC),
        metadata=goal.metadata,
    )
