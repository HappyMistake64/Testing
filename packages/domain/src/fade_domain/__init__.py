"""FADE domain layer - pure business models and rules."""

from fade_domain.evidence import EvidenceEvent
from fade_domain.goal import Goal, GoalStatus
from fade_domain.ids import (
    ArtifactId,
    EvidenceId,
    GoalId,
    JobId,
    PlanId,
    ProfileId,
    ProjectId,
)
from fade_domain.job import Job, JobState, can_transition, is_terminal
from fade_domain.plan import Plan, PlanStatus, PlanStep
from fade_domain.project import (
    GitMetadata,
    InventorySummary,
    PreflightIssue,
    PreflightReport,
    Project,
    ProjectStatus,
    SourceType,
)
from fade_domain.project_profile import ProjectProfile, SymbolEntry
from fade_domain.types import AutonomyLevel, ErrorCode, RiskLevel

__all__ = [
    "ArtifactId",
    "AutonomyLevel",
    "ErrorCode",
    "EvidenceEvent",
    "EvidenceId",
    "GitMetadata",
    "Goal",
    "GoalId",
    "GoalStatus",
    "InventorySummary",
    "Job",
    "JobId",
    "JobState",
    "Plan",
    "PlanId",
    "PlanStatus",
    "PlanStep",
    "PreflightIssue",
    "PreflightReport",
    "ProfileId",
    "Project",
    "ProjectId",
    "ProjectProfile",
    "ProjectStatus",
    "RiskLevel",
    "SourceType",
    "SymbolEntry",
    "can_transition",
    "is_terminal",
]
