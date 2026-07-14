"""Durable DB-backed job queue with claim and heartbeat."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fade_application.ports import JobQueuePort, JobRepositoryPort
from fade_domain.ids import JobId
from fade_domain.job import Job, JobState
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import JobModel


class SqlAlchemyJobQueue(JobQueuePort):
    """Claim queued jobs with lease-based worker coordination."""

    def __init__(self, session: AsyncSession, repository: JobRepositoryPort) -> None:
        self._session = session
        self._repository = repository

    async def claim_next(self, worker_id: str, *, lease_seconds: int = 60) -> Job | None:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(JobModel)
            .where(JobModel.state == JobState.QUEUED.value)
            .order_by(JobModel.created_at)
            .limit(1)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None

        lease_until = now + timedelta(seconds=lease_seconds)
        await self._session.execute(
            update(JobModel)
            .where(JobModel.id == model.id, JobModel.state == JobState.QUEUED.value)
            .values(
                state=JobState.RUNNING.value,
                worker_id=worker_id,
                lease_expires_at=lease_until,
                updated_at=now,
            )
        )
        await self._session.commit()
        job = await self._repository.get_by_id(JobId(model.id))
        return job

    async def heartbeat(self, job_id: JobId, worker_id: str, *, lease_seconds: int = 60) -> bool:
        now = datetime.now(UTC)
        lease_until = now + timedelta(seconds=lease_seconds)
        result = await self._session.execute(
            update(JobModel)
            .where(
                JobModel.id == str(job_id),
                JobModel.worker_id == worker_id,
                JobModel.state == JobState.RUNNING.value,
            )
            .values(lease_expires_at=lease_until, updated_at=now)
        )
        await self._session.commit()
        return result.rowcount > 0  # type: ignore[attr-defined,no-any-return]

    async def release_stale(self, *, grace_seconds: int = 120) -> int:
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=grace_seconds)
        result = await self._session.execute(
            select(JobModel).where(
                JobModel.state == JobState.RUNNING.value,
                JobModel.lease_expires_at.is_not(None),
                JobModel.lease_expires_at < cutoff,
            )
        )
        stale = list(result.scalars())
        count = 0
        for model in stale:
            model.state = JobState.QUEUED.value
            model.worker_id = None
            model.lease_expires_at = None
            model.updated_at = now
            count += 1
        if count:
            await self._session.commit()
        return count
