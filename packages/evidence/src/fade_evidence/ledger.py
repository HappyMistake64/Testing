"""Append-only evidence hash chain."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fade_domain.evidence import EvidenceEvent
from fade_domain.ids import EvidenceId, JobId, ProjectId


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Compute stable hash of event payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_hex(canonical)


def compute_event_hash(
    *,
    sequence: int,
    event_type: str,
    payload_hash: str,
    previous_event_hash: str | None,
    timestamp: datetime,
) -> str:
    """Compute hash for an evidence event linking to previous."""
    parts = [
        str(sequence),
        event_type,
        payload_hash,
        previous_event_hash or "",
        timestamp.isoformat(),
    ]
    return _sha256_hex("|".join(parts))


@dataclass
class EvidenceLedger:
    """In-memory evidence chain builder and validator."""

    _previous_hash: str | None = None
    _sequence: int = 0

    @property
    def previous_hash(self) -> str | None:
        return self._previous_hash

    @property
    def sequence(self) -> int:
        return self._sequence

    def append(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        project_id: ProjectId | None = None,
        job_id: JobId | None = None,
        actor_type: str = "system",
        actor_id: str = "fade",
    ) -> EvidenceEvent:
        """Create next event in the hash chain."""
        self._sequence += 1
        now = datetime.now(UTC)
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload_hash = compute_payload_hash(payload)
        event_hash = compute_event_hash(
            sequence=self._sequence,
            event_type=event_type,
            payload_hash=payload_hash,
            previous_event_hash=self._previous_hash,
            timestamp=now,
        )
        event = EvidenceEvent(
            id=EvidenceId.generate(),
            sequence=self._sequence,
            project_id=project_id,
            job_id=job_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            payload_json=payload_json,
            payload_hash=payload_hash,
            previous_event_hash=self._previous_hash,
            event_hash=event_hash,
            timestamp=now,
        )
        self._previous_hash = event_hash
        return event

    @staticmethod
    def verify_chain(events: list[EvidenceEvent]) -> bool:
        """Verify integrity of an ordered evidence chain."""
        previous: str | None = None
        for i, event in enumerate(events, start=1):
            if event.sequence != i:
                return False
            if event.previous_event_hash != previous:
                return False
            expected_payload_hash = _sha256_hex(
                json.dumps(json.loads(event.payload_json), sort_keys=True, separators=(",", ":"))
            )
            if event.payload_hash != expected_payload_hash:
                return False
            expected_event_hash = compute_event_hash(
                sequence=event.sequence,
                event_type=event.event_type,
                payload_hash=event.payload_hash,
                previous_event_hash=event.previous_event_hash,
                timestamp=event.timestamp,
            )
            if event.event_hash != expected_event_hash:
                return False
            previous = event.event_hash
        return True

    @classmethod
    def from_events(cls, events: list[EvidenceEvent]) -> EvidenceLedger:
        """Restore ledger state from existing events."""
        ledger = cls()
        for event in sorted(events, key=lambda e: e.sequence):
            ledger._sequence = event.sequence
            ledger._previous_hash = event.event_hash
        return ledger
