"""Goal domain entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from fade_domain.ids import GoalId, ProjectId


class GoalStatus(StrEnum):
    """Goal lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Goal:
    """User or system objective for a project."""

    id: GoalId
    project_id: ProjectId
    title: str
    intent: str
    constraints: list[str]
    priority: int
    status: GoalStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, object] = field(default_factory=dict)
