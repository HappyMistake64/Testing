"""Job queue resource budget unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fade_domain.ids import JobId, ProjectId
from fade_domain.job import Job, JobState
from fade_domain.types import AutonomyLevel
from fade_infrastructure.database import Base
from fade_infrastructure.job_queue import SqlAlchemyJobQueue
from fade_infrastructure.job_repository import SqlAlchemyJobRepository
from fade_infrastructure.job_resource import JobResourceClass, classify_job
from fade_infrastructure.models import JobModel  # noqa: F401
from fade_infrastructure.settings import Settings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _job(
    *,
    job_id: str,
    job_type: str,
    state: JobState = JobState.QUEUED,
    budgets: dict[str, object] | None = None,
) -> Job:
    now = datetime.now(UTC)
    return Job(
        id=JobId.from_string(job_id),
        project_id=ProjectId.generate(),
        job_type=job_type,
        state=state,
        autonomy_level=AutonomyLevel.ASSISTED,
        payload={},
        worker_id="worker-a" if state == JobState.RUNNING else None,
        lease_expires_at=now if state == JobState.RUNNING else None,
        created_at=now,
        updated_at=now,
        budgets=budgets or {},
    )


@pytest_asyncio.fixture
async def queue_session(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'job_queue.db'}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        max_concurrent_heavy_jobs=1,
        max_concurrent_light_jobs=2,
    )

    async with session_factory() as session:
        yield session, settings

    await engine.dispose()


class TestJobResourceClassification:
    def test_known_light_job_types(self) -> None:
        assert classify_job("noop") == JobResourceClass.LIGHT
        assert classify_job("analyze") == JobResourceClass.LIGHT

    def test_unknown_job_types_default_to_heavy(self) -> None:
        assert classify_job("implementation") == JobResourceClass.HEAVY
        assert classify_job("workspace") == JobResourceClass.HEAVY

    def test_explicit_budget_override(self) -> None:
        assert classify_job("custom", {"resource_class": "light"}) == JobResourceClass.LIGHT
        assert classify_job("noop", {"resource_class": "heavy"}) == JobResourceClass.HEAVY


class TestSqlAlchemyJobQueueBudgets:
    @pytest.mark.asyncio
    async def test_claim_next_respects_heavy_budget(self, queue_session) -> None:
        session, settings = queue_session
        repository = SqlAlchemyJobRepository(session)
        queue = SqlAlchemyJobQueue(session, repository, settings)

        await repository.create(
            _job(job_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", job_type="implementation")
        )
        await repository.create(
            _job(job_id="01ARZ3NDEKTSV4RRFFQ69G5FAW", job_type="implementation")
        )
        running = _job(
            job_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
            job_type="implementation",
            state=JobState.RUNNING,
        )
        await repository.create(running)

        claimed = await queue.claim_next("worker-b")
        assert claimed is None

    @pytest.mark.asyncio
    async def test_claim_next_allows_light_jobs_within_budget(self, queue_session) -> None:
        session, settings = queue_session
        repository = SqlAlchemyJobRepository(session)
        queue = SqlAlchemyJobQueue(session, repository, settings)

        await repository.create(_job(job_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", job_type="noop"))
        await repository.create(
            _job(
                job_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
                job_type="noop",
                state=JobState.RUNNING,
            )
        )
        await repository.create(
            _job(
                job_id="01ARZ3NDEKTSV4RRFFQ69G5FAY",
                job_type="noop",
                state=JobState.RUNNING,
            )
        )

        claimed = await queue.claim_next("worker-b")
        assert claimed is None

    @pytest.mark.asyncio
    async def test_claim_next_skips_blocked_job_and_claims_next_eligible(
        self,
        queue_session,
    ) -> None:
        session, settings = queue_session
        repository = SqlAlchemyJobRepository(session)
        queue = SqlAlchemyJobQueue(session, repository, settings)

        await repository.create(
            _job(job_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", job_type="implementation")
        )
        await repository.create(_job(job_id="01ARZ3NDEKTSV4RRFFQ69G5FAW", job_type="noop"))
        await repository.create(
            _job(
                job_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
                job_type="implementation",
                state=JobState.RUNNING,
            )
        )

        claimed = await queue.claim_next("worker-b")
        assert claimed is not None
        assert claimed.job_type == "noop"
        assert claimed.state == JobState.RUNNING

    @pytest.mark.asyncio
    async def test_claim_next_claims_when_budget_available(self, queue_session) -> None:
        session, settings = queue_session
        repository = SqlAlchemyJobRepository(session)
        queue = SqlAlchemyJobQueue(session, repository, settings)

        await repository.create(_job(job_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", job_type="noop"))

        claimed = await queue.claim_next("worker-b")
        assert claimed is not None
        assert claimed.job_type == "noop"
        assert claimed.worker_id == "worker-b"
