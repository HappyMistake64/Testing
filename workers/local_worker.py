"""Local durable job worker with claim and heartbeat."""

from __future__ import annotations

import argparse
import asyncio
import signal
import uuid
from datetime import UTC, datetime

from fade_agent_runtime.assistant_orchestrator import AssistantOrchestrator
from fade_agent_runtime.orchestrator import AgentRuntimeOrchestrator
from fade_application.assistant import AssistantService
from fade_domain.assistant import CommandMode
from fade_domain.job import JobState
from fade_evidence.ledger import EvidenceLedger
from fade_infrastructure.assistant_repository import SqlAlchemyAssistantRepository
from fade_infrastructure.automation_repository import SqlAlchemyAutomationRepository
from fade_infrastructure.database import create_engine, create_session_factory
from fade_infrastructure.evidence_repository import SqlAlchemyEvidenceRepository
from fade_infrastructure.job_queue import SqlAlchemyJobQueue
from fade_infrastructure.job_repository import SqlAlchemyJobRepository
from fade_infrastructure.logging import configure_logging, get_logger
from fade_infrastructure.memory_repository import SqlAlchemyMemoryRepository
from fade_infrastructure.project_repository import SqlAlchemyProjectRepository
from fade_infrastructure.settings import get_settings
from fade_model_router.router import create_default_router

logger = get_logger(__name__)


class LocalWorker:
    """Poll queue, claim jobs, send heartbeats, and execute via agent runtime."""

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
        self._model_router = create_default_router(
            openai_api_key=(
                settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
            ),
            ollama_base_url=settings.ollama_base_url,
            ollama_default_model=settings.ollama_default_model,
            include_stub=settings.env in {"test", "development"},
        )
        self._orchestrator = AgentRuntimeOrchestrator(
            settings,
            self._session_factory,
            self._model_router,
        )
        self._assistant = AssistantOrchestrator(
            settings,
            self._session_factory,
            self._model_router,
        )
        self._orchestrator.attach_assistant(self._assistant)

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

                await self._schedule_due_automations(session)

                job = await queue.claim_next(self._worker_id, lease_seconds=self._lease_seconds)
                if job is None:
                    await asyncio.sleep(self._poll_interval)
                    continue

                await self._record_event(
                    evidence, job, "JOB_STARTED", {"worker_id": self._worker_id}
                )
                logger.info("worker_claimed_job", job_id=str(job.id), job_type=job.job_type)

                try:
                    await self._orchestrator.execute_job(job.id, worker_id=self._worker_id)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("worker_job_failed", job_id=str(job.id), error=str(exc))
                    failed = await repository.get_by_id(job.id)
                    if failed and failed.state not in {
                        JobState.COMPLETED,
                        JobState.FAILED,
                        JobState.CANCELLED,
                    }:
                        failed = _with_state(failed, JobState.FAILED)
                        await repository.update(failed)
                        await self._record_event(
                            evidence, failed, "JOB_FAILED", {"error": str(exc)}
                        )
                await asyncio.sleep(self._poll_interval)

        await self._engine.dispose()
        logger.info("worker_stopped", worker_id=self._worker_id)

    async def _schedule_due_automations(self, session) -> None:
        """Turn due user-created automations into assistant turn jobs."""
        assistant_repo = SqlAlchemyAssistantRepository(session)
        if await assistant_repo.is_paused():
            return
        automations = SqlAlchemyAutomationRepository(session)
        due = await automations.claim_due()
        if not due:
            return
        service = AssistantService(
            repository=assistant_repo,
            memory=SqlAlchemyMemoryRepository(session),
            jobs=SqlAlchemyJobRepository(session),
            projects=SqlAlchemyProjectRepository(session),
            automations=automations,
        )
        automation_session = await service.ensure_automation_session()
        for automation in due:
            turn = await service.create_turn(
                automation_session.id,
                command=automation.command,
                mode=CommandMode.EXECUTE,
            )
            logger.info(
                "worker_automation_triggered",
                automation_id=automation.id,
                turn_id=str(turn.id),
            )

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
