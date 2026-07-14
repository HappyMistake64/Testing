"""Local durable job worker with claim and heartbeat."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import uuid
from datetime import UTC, datetime

from fade_domain.ids import JobId
from fade_domain.job import JobState
from fade_evidence.ledger import EvidenceLedger
from fade_infrastructure.database import create_engine, create_session_factory
from fade_infrastructure.evidence_repository import SqlAlchemyEvidenceRepository
from fade_infrastructure.job_queue import SqlAlchemyJobQueue
from fade_infrastructure.job_repository import SqlAlchemyJobRepository
from fade_infrastructure.logging import configure_logging, get_logger
from fade_infrastructure.settings import get_settings

logger = get_logger(__name__)


class LocalWorker:
    """Poll queue, claim jobs, send heartbeats, and execute lightweight handlers."""

    def __init__(
        self,
        *,
        worker_id: str | None = None,
        poll_interval: float = 2.0,
        lease_seconds: int = 60,
    ) -> None:
        self._worker_id = worker_id or f"local-{uuid.uuid4().hex[:8]}"
        self._poll_interval = poll_interval
        self._lease_seconds = lease_seconds
        self._running = True
        settings = get_settings()
        configure_logging(settings)
        self._engine = create_engine(settings)
        self._session_factory = create_session_factory(self._engine)

    async def run(self) -> None:
        logger.info("worker_starting", worker_id=self._worker_id)
        while self._running:
            async with self._session_factory() as session:
                queue = SqlAlchemyJobQueue(session, SqlAlchemyJobRepository(session))
                repository = SqlAlchemyJobRepository(session)
                evidence = SqlAlchemyEvidenceRepository(session)

                released = await queue.release_stale()
                if released:
                    logger.info("worker_released_stale_jobs", count=released)

                job = await queue.claim_next(self._worker_id, lease_seconds=self._lease_seconds)
                if job is None:
                    await asyncio.sleep(self._poll_interval)
                    continue

                await self._record_event(evidence, job, "JOB_STARTED", {"worker_id": self._worker_id})
                logger.info("worker_claimed_job", job_id=str(job.id), job_type=job.job_type)

                try:
                    await self._execute_job(job, queue, repository, evidence)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("worker_job_failed", job_id=str(job.id), error=str(exc))
                    failed = await repository.get_by_id(job.id)
                    if failed:
                        failed = _with_state(failed, JobState.FAILED)
                        await repository.update(failed)
                        await self._record_event(
                            evidence, failed, "JOB_FAILED", {"error": str(exc)}
                        )
                await asyncio.sleep(self._poll_interval)

        await self._engine.dispose()
        logger.info("worker_stopped", worker_id=self._worker_id)

    async def _execute_job(self, job, queue, repository, evidence) -> None:
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(job.id, queue)
        )
        try:
            if job.job_type == "noop":
                await asyncio.sleep(0.1)
            elif job.job_type == "analyze":
                await asyncio.sleep(0.2)
            else:
                await asyncio.sleep(0.1)

            current = await repository.get_by_id(job.id)
            if current and current.state == JobState.RUNNING:
                completed = _with_state(current, JobState.COMPLETED)
                await repository.update(completed)
                await self._record_event(
                    evidence, completed, "JOB_FINISHED", {"worker_id": self._worker_id}
                )
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

    async def _heartbeat_loop(self, job_id: JobId, queue: SqlAlchemyJobQueue) -> None:
        while True:
            await asyncio.sleep(self._lease_seconds / 2)
            async with self._session_factory() as session:
                hb_queue = SqlAlchemyJobQueue(session, SqlAlchemyJobRepository(session))
                ok = await hb_queue.heartbeat(
                    job_id, self._worker_id, lease_seconds=self._lease_seconds
                )
                if not ok:
                    break

    async def _record_event(self, evidence, job, event_type: str, payload: dict) -> None:
        events = await evidence.list_for_job(job.id)
        ledger = EvidenceLedger.from_events(events)
        event = ledger.append(
            event_type=event_type,
            payload=payload,
            project_id=job.project_id,
            job_id=job.id,
            actor_type="worker",
            actor_id=self._worker_id,
        )
        await evidence.append(event)

    def stop(self) -> None:
        self._running = False


def _with_state(job, state: JobState):
    from fade_domain.job import Job

    return Job(
        id=job.id,
        project_id=job.project_id,
        job_type=job.job_type,
        state=state,
        autonomy_level=job.autonomy_level,
        payload=job.payload,
        worker_id=job.worker_id,
        lease_expires_at=job.lease_expires_at,
        created_at=job.created_at,
        updated_at=datetime.now(UTC),
        checkpoint=job.checkpoint,
        budgets=job.budgets,
    )


async def _main() -> None:
    parser = argparse.ArgumentParser(description="FADE local job worker")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    args = parser.parse_args()

    worker = LocalWorker(worker_id=args.worker_id, poll_interval=args.poll_interval)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)

    await worker.run()


if __name__ == "__main__":
    asyncio.run(_main())
