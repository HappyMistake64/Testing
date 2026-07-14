"""Plan domain entity and structured plan types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from fade_domain.ids import GoalId, PlanId
from fade_domain.types import RiskLevel


class PlanStatus(StrEnum):
    """Plan lifecycle status."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class PlanStep:
    """Single step in an execution plan."""

    ordinal: int
    title: str
    description: str
    step_type: str
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Plan:
    """Approved or proposed approach to achieve a goal."""

    id: PlanId
    goal_id: GoalId
    version: int
    status: PlanStatus
    assumptions: list[str]
    steps: list[PlanStep]
    test_plan: list[str]
    risk_level: RiskLevel
    created_at: datetime
    approved_at: datetime | None = None
    model_id: str | None = None
    raw_output: str | None = None
