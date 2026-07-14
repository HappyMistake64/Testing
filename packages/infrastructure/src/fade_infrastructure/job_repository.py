"""Job repository SQLAlchemy implementation."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fade_application.ports import JobRepositoryPort
from fade_domain.ids import JobId, ProjectId
from fade_domain.job import Job, JobState
from fade_domain.types import AutonomyLevel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import JobModel


class SqlAlchemyJobRepository(JobRepositoryPort):
    """Persist jobs in SQLite."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job: Job) -> Job:
        model = _to_model(job)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)

    async def get_by_id(self, job_id: JobId) -> Job | None:
        result = await self._session.execute(
            select(JobModel).where(JobModel.id == str(job_id))
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def update(self, job: Job) -> Job:
        result = await self._session.execute(
            select(JobModel).where(JobModel.id == str(job.id))
        )
        model = result.scalar_one()
        model.state = job.state.value
        model.autonomy_level = job.autonomy_level.value
        model.payload_json = json.dumps(job.payload)
        model.checkpoint_json = json.dumps(job.checkpoint)
        model.budgets_json = json.dumps(job.budgets)
        model.worker_id = job.worker_id
        model.lease_expires_at = job.lease_expires_at
        model.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)

    async def list_by_project(self, project_id: ProjectId) -> list[Job]:
        result = await self._session.execute(
            select(JobModel)
            .where(JobModel.project_id == str(project_id))
            .order_by(JobModel.created_at.desc())
        )
        return [_to_domain(row) for row in result.scalars()]


def _to_model(job: Job) -> JobModel:
    return JobModel(
        id=str(job.id),
        project_id=str(job.project_id),
        job_type=job.job_type,
        state=job.state.value,
        autonomy_level=job.autonomy_level.value,
        payload_json=json.dumps(job.payload),
        checkpoint_json=json.dumps(job.checkpoint),
        budgets_json=json.dumps(job.budgets),
        worker_id=job.worker_id,
        lease_expires_at=job.lease_expires_at,
    )


def _to_domain(model: JobModel) -> Job:
    return Job(
        id=JobId(model.id),
        project_id=ProjectId(model.project_id),
        job_type=model.job_type,
        state=JobState(model.state),
        autonomy_level=AutonomyLevel(model.autonomy_level),
        payload=json.loads(model.payload_json),
        checkpoint=json.loads(model.checkpoint_json),
        budgets=json.loads(model.budgets_json),
        worker_id=model.worker_id,
        lease_expires_at=model.lease_expires_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
