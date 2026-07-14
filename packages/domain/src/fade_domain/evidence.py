"""Evidence ledger domain types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fade_domain.ids import EvidenceId, JobId, ProjectId


@dataclass(frozen=True, slots=True)
class EvidenceEvent:
    """Append-only audit event in the evidence chain."""

    id: EvidenceId
    sequence: int
    project_id: ProjectId | None
    job_id: JobId | None
    actor_type: str
    actor_id: str
    event_type: str
    payload_json: str
    payload_hash: str
    previous_event_hash: str | None
    event_hash: str
    timestamp: datetime
