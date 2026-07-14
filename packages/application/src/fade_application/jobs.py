"""Job application service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fade_domain.evidence import EvidenceEvent
from fade_domain.ids import JobId, ProjectId, WorkspaceId
from fade_domain.job import Job, JobState, can_transition
from fade_domain.types import AutonomyLevel
from fade_evidence.ledger import EvidenceLedger
from fade_infrastructure.workspace_repository import SqlAlchemyWorkspaceRepository
from fade_repair_loop.repair_loop import RepairLoop, RepairLoopConfig
from fade_tool_gateway.gateway import ToolGateway
from fade_verification.gates import VerificationGate
from fade_verification.verification_matrix import VerificationMatrix, VerificationResult

from fade_application.ports import EvidencePort, JobRepositoryPort


@dataclass(frozen=True, slots=True)
class CreateJobCommand:
    project_id: ProjectId
    job_type: str
    payload: dict[str, object]
    autonomy_level: AutonomyLevel = AutonomyLevel.ASSISTED


class JobService:
    """Durable job lifecycle, verification, and repair."""

    def __init__(
        self,
        *,
        repository: JobRepositoryPort,
        evidence: EvidencePort,
        workspace_repository: SqlAlchemyWorkspaceRepository | None = None,
        repair_loop: RepairLoop | None = None,
    ) -> None:
        self._repository = repository
        self._evidence = evidence
        self._workspaces = workspace_repository
        self._repair_loop = repair_loop or RepairLoop(RepairLoopConfig())
        self._ledger = EvidenceLedger()

    async def create_job(self, command: CreateJobCommand) -> Job:
        now = datetime.now(UTC)
        job = Job(
            id=JobId.generate(),
            project_id=command.project_id,
            job_type=command.job_type,
            state=JobState.QUEUED,
            autonomy_level=command.autonomy_level,
            payload=command.payload,
            worker_id=None,
            lease_expires_at=None,
            created_at=now,
            updated_at=now,
        )
        saved = await self._repository.create(job)
        await self._append_event(saved, "JOB_CREATED", {"job_type": command.job_type})
        return saved

    async def get_job(self, job_id: JobId) -> Job | None:
        return await self._repository.get_by_id(job_id)

    async def pause_job(self, job_id: JobId) -> Job | None:
        return await self._transition(job_id, JobState.PAUSED, "JOB_PAUSED")

    async def resume_job(self, job_id: JobId) -> Job | None:
        return await self._transition(job_id, JobState.RUNNING, "JOB_RESUMED")

    async def cancel_job(self, job_id: JobId) -> Job | None:
        return await self._transition(job_id, JobState.CANCELLED, "JOB_CANCELLED")

    async def list_events_since(self, job_id: JobId, after_sequence: int) -> list[EvidenceEvent]:
        return await self._evidence.list_since(job_id, after_sequence)

    async def verify_job(
        self,
        job_id: JobId,
        *,
        matrix: VerificationMatrix | None = None,
    ):
        job = await self._repository.get_by_id(job_id)
        if job is None:
            return None
        if self._workspaces is None:
            raise ValueError("Workspace repository not configured")

        workspace_id = self._workspace_id_from_job(job)
        if workspace_id is None:
            raise ValueError("Job has no workspace")

        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise ValueError("Workspace not found")

        gateway = ToolGateway.for_workspace(Path(workspace.path))
        gate = VerificationGate(gateway)
        result = gate.run(matrix or VerificationMatrix.minimal())

        target_state = (
            JobState.COMPLETED
            if result.result in {VerificationResult.PASS, VerificationResult.PASS_WITH_WARNINGS}
            else JobState.REPAIRING
        )
        if not can_transition(job.state, JobState.VERIFYING):
            job = await self._set_state(job, JobState.VERIFYING)
        updated = await self._set_state(
            await self._update_checkpoint(
                job,
                last_verification_result=result.result.value,
            ),
            target_state,
        )
        await self._append_event(
            updated,
            "VERIFICATION_FINISHED",
            {"result": result.result.value, "summary": result.summary},
        )
        return result, updated

    async def repair_job(
        self,
        job_id: JobId,
        *,
        patch_content: str,
        log_excerpt: str = "",
    ):
        job = await self._repository.get_by_id(job_id)
        if job is None:
            return None

        checkpoint = dict(job.checkpoint)
        iteration = int(checkpoint.get("repair_iteration", 0))
        repair_hashes = list(checkpoint.get("repair_hashes", []))
        last_result = checkpoint.get("last_verification_result")
        verification_result = (
            VerificationResult(str(last_result)) if last_result else VerificationResult.INCONCLUSIVE
        )

        iteration_result = self._repair_loop.run_iteration(
            iteration=iteration,
            patch_content=patch_content,
            verification_result=verification_result,
            log_excerpt=log_excerpt,
        )

        if iteration_result.patch_hash and iteration_result.patch_hash not in repair_hashes:
            repair_hashes.append(iteration_result.patch_hash)

        checkpoint["repair_iteration"] = iteration + 1
        checkpoint["repair_hashes"] = repair_hashes

        new_state = JobState.BLOCKED if iteration_result.blocked else JobState.REPAIRING
        updated = Job(
            id=job.id,
            project_id=job.project_id,
            job_type=job.job_type,
            state=new_state,
            autonomy_level=job.autonomy_level,
            payload=job.payload,
            worker_id=job.worker_id,
            lease_expires_at=job.lease_expires_at,
            created_at=job.created_at,
            updated_at=datetime.now(UTC),
            checkpoint=checkpoint,
            budgets=job.budgets,
        )
        saved = await self._repository.update(updated)
        await self._append_event(
            saved,
            "REPAIR_ITERATION",
            {
                "iteration": iteration_result.iteration,
                "blocked": iteration_result.blocked,
                "patch_hash": iteration_result.patch_hash,
            },
        )
        return iteration_result, saved

    async def _transition(
        self,
        job_id: JobId,
        target: JobState,
        event_type: str,
    ) -> Job | None:
        job = await self._repository.get_by_id(job_id)
        if job is None or not can_transition(job.state, target):
            return None
        updated = await self._set_state(job, target)
        await self._append_event(updated, event_type, {"state": target.value})
        return updated

    async def _set_state(self, job: Job, state: JobState) -> Job:
        updated = Job(
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
        return await self._repository.update(updated)

    async def _update_checkpoint(self, job: Job, **fields: object) -> Job:
        checkpoint = dict(job.checkpoint)
        checkpoint.update(fields)
        updated = Job(
            id=job.id,
            project_id=job.project_id,
            job_type=job.job_type,
            state=job.state,
            autonomy_level=job.autonomy_level,
            payload=job.payload,
            worker_id=job.worker_id,
            lease_expires_at=job.lease_expires_at,
            created_at=job.created_at,
            updated_at=datetime.now(UTC),
            checkpoint=checkpoint,
            budgets=job.budgets,
        )
        return await self._repository.update(updated)

    def _workspace_id_from_job(self, job: Job) -> WorkspaceId | None:
        raw = job.checkpoint.get("workspace_id") or job.payload.get("workspace_id")
        if raw is None:
            return None
        return WorkspaceId.from_string(str(raw))

    async def _append_event(self, job: Job, event_type: str, payload: dict[str, object]) -> None:
        events = await self._evidence.list_for_job(job.id)
        ledger = EvidenceLedger.from_events(events) if events else self._ledger
        event = ledger.append(
            event_type=event_type,
            payload=payload,
            project_id=job.project_id,
            job_id=job.id,
        )
        await self._evidence.append(event)
