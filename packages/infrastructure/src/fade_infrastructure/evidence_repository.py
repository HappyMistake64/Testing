"""Evidence ledger persistence via job_events table."""

from __future__ import annotations

from datetime import UTC

from fade_application.ports import EvidencePort
from fade_domain.evidence import EvidenceEvent
from fade_domain.ids import EvidenceId, JobId, ProjectId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import JobEventModel


class SqlAlchemyEvidenceRepository(EvidencePort):
    """Append-only evidence event store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: EvidenceEvent) -> EvidenceEvent:
        model = JobEventModel(
            id=str(event.id),
            sequence=event.sequence,
            project_id=str(event.project_id) if event.project_id else None,
            job_id=str(event.job_id) if event.job_id else None,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            event_type=event.event_type,
            payload_json=event.payload_json,
            payload_hash=event.payload_hash,
            previous_event_hash=event.previous_event_hash,
            event_hash=event.event_hash,
            created_at=event.timestamp,
        )
        self._session.add(model)
        await self._session.commit()
        return event

    async def list_for_job(self, job_id: JobId) -> list[EvidenceEvent]:
        result = await self._session.execute(
            select(JobEventModel)
            .where(JobEventModel.job_id == str(job_id))
            .order_by(JobEventModel.sequence)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def list_since(self, job_id: JobId, after_sequence: int) -> list[EvidenceEvent]:
        result = await self._session.execute(
            select(JobEventModel)
            .where(
                JobEventModel.job_id == str(job_id),
                JobEventModel.sequence > after_sequence,
            )
            .order_by(JobEventModel.sequence)
        )
        return [_to_domain(row) for row in result.scalars()]


def _to_domain(model: JobEventModel) -> EvidenceEvent:
    ts = model.created_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return EvidenceEvent(
        id=EvidenceId(model.id),
        sequence=model.sequence,
        project_id=ProjectId(model.project_id) if model.project_id else None,
        job_id=JobId(model.job_id) if model.job_id else None,
        actor_type=model.actor_type,
        actor_id=model.actor_id,
        event_type=model.event_type,
        payload_json=model.payload_json,
        payload_hash=model.payload_hash,
        previous_event_hash=model.previous_event_hash,
        event_hash=model.event_hash,
        timestamp=ts,
    )
