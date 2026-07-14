"""Job domain entity and state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from fade_domain.ids import JobId, ProjectId
from fade_domain.types import AutonomyLevel


class JobState(StrEnum):
    """Durable job lifecycle states."""

    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    PAUSED = "paused"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


_TERMINAL_STATES = frozenset({JobState.COMPLETED, JobState.CANCELLED, JobState.FAILED})

_VALID_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.QUEUED: frozenset({JobState.PREPARING, JobState.CANCELLED, JobState.FAILED}),
    JobState.PREPARING: frozenset({JobState.RUNNING, JobState.CANCELLED, JobState.FAILED}),
    JobState.RUNNING: frozenset({
        JobState.PAUSED,
        JobState.VERIFYING,
        JobState.BLOCKED,
        JobState.CANCELLED,
        JobState.FAILED,
        JobState.COMPLETED,
    }),
    JobState.PAUSED: frozenset({JobState.RUNNING, JobState.CANCELLED, JobState.FAILED}),
    JobState.VERIFYING: frozenset({
        JobState.REPAIRING,
        JobState.COMPLETED,
        JobState.FAILED,
        JobState.BLOCKED,
    }),
    JobState.REPAIRING: frozenset({JobState.VERIFYING, JobState.FAILED, JobState.CANCELLED}),
    JobState.BLOCKED: frozenset({JobState.RUNNING, JobState.CANCELLED, JobState.FAILED}),
    JobState.COMPLETED: frozenset(),
    JobState.CANCELLED: frozenset(),
    JobState.FAILED: frozenset(),
}


def can_transition(current: JobState, target: JobState) -> bool:
    """Return whether a job state transition is valid."""
    return target in _VALID_TRANSITIONS.get(current, frozenset())


def is_terminal(state: JobState) -> bool:
    """Return whether the job state is terminal."""
    return state in _TERMINAL_STATES


@dataclass(frozen=True, slots=True)
class Job:
    """Persistent job execution record."""

    id: JobId
    project_id: ProjectId
    job_type: str
    state: JobState
    autonomy_level: AutonomyLevel
    payload: dict[str, object]
    worker_id: str | None
    lease_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    checkpoint: dict[str, object] = field(default_factory=dict)
    budgets: dict[str, object] = field(default_factory=dict)
