"""Agent runtime orchestrator for durable jobs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fade_domain.goal import Goal
from fade_domain.ids import JobId, PlanId, WorkspaceId
from fade_domain.job import Job, JobState, can_transition
from fade_domain.plan import Plan
from fade_domain.project import Project
from fade_domain.project_profile import ProjectProfile
from fade_domain.workspace import Workspace, WorkspaceState
from fade_evidence.ledger import EvidenceLedger
from fade_infrastructure.artifact_store import ArtifactStore
from fade_infrastructure.evidence_repository import SqlAlchemyEvidenceRepository
from fade_infrastructure.goal_repository import SqlAlchemyGoalRepository
from fade_infrastructure.job_repository import SqlAlchemyJobRepository
from fade_infrastructure.plan_repository import SqlAlchemyPlanRepository
from fade_infrastructure.project_analysis_service import ProjectAnalysisService
from fade_infrastructure.project_repository import SqlAlchemyProjectRepository
from fade_infrastructure.settings import Settings
from fade_infrastructure.workspace_manager import WorkspaceManager
from fade_infrastructure.workspace_repository import SqlAlchemyWorkspaceRepository
from fade_model_router.router import ModelRouter
from fade_patch_engine.patch import PatchEngineError
from fade_repair_loop.repair_loop import RepairLoop, RepairLoopConfig
from fade_tool_gateway.gateway import ToolGateway, ToolGatewayError
from fade_verification.gates import VerificationGate
from fade_verification.verification_matrix import VerificationResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fade_agent_runtime.agent_loop import gather_context_via_tools
from fade_agent_runtime.diff import parse_unified_diff
from fade_agent_runtime.implementation import (
    ImplementationParseError,
    apply_implementation,
    parse_implementation_output,
)
from fade_agent_runtime.promotion import (
    PromotionError,
    promote_workspace_to_source,
    workspace_diff_text,
)
from fade_agent_runtime.prompts import IMPLEMENTATION_SYSTEM_PROMPT, REPAIR_SYSTEM_PROMPT
from fade_agent_runtime.verification import matrix_for_workspace
from fade_agent_runtime.verification_serialize import serialize_verification


class AgentRuntimeOrchestrator:
    """Execute queued jobs with workspace isolation, tools, patch, and verification."""

    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        model_router: ModelRouter,
        *,
        repair_loop: RepairLoop | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._model_router = model_router
        self._workspace_manager = WorkspaceManager(settings.workspaces_dir)
        self._repair_loop = repair_loop or RepairLoop(RepairLoopConfig())

    async def execute_job(self, job_id: JobId, *, worker_id: str = "runtime") -> Job:
        async with self._session_factory() as session:
            repositories = _Repositories(session)
            job = await repositories.jobs.get_by_id(job_id)
            if job is None:
                msg = f"Job not found: {job_id}"
                raise ValueError(msg)

            if job.job_type == "noop":
                return await self._complete_job(repositories, job, worker_id, {"noop": True})
            if job.job_type == "analyze":
                return await self._execute_analyze(repositories, job, worker_id)
            if job.job_type == "implementation":
                return await self._execute_implementation(repositories, job, worker_id)

            return await self._fail_job(
                repositories,
                job,
                worker_id,
                error=f"Unsupported job type: {job.job_type}",
            )

    async def get_job_diff(self, job_id: JobId) -> dict[str, object] | None:
        async with self._session_factory() as session:
            repositories = _Repositories(session)
            job = await repositories.jobs.get_by_id(job_id)
            if job is None:
                return None

            workspace_id = _workspace_id_from_job(job)
            if workspace_id is None:
                return None

            workspace = await repositories.workspaces.get_by_id(workspace_id)
            if workspace is None:
                return None

            gateway = ToolGateway.for_workspace(
                Path(workspace.path),
                lease_token=workspace.lease.token if workspace.lease else None,
                expected_lease_token=workspace.lease.token if workspace.lease else None,
                write_allowed=False,
            )
            diff_result = gateway.git_diff()
            files = parse_unified_diff(diff_result.diff)
            review_status = str(job.checkpoint.get("review_status", "pending"))
            verification = job.checkpoint.get("verification")
            return {
                "job_id": str(job_id),
                "base_revision": workspace.base_revision or "",
                "files": [
                    {
                        "path": file.path,
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "patch": file.patch,
                    }
                    for file in files
                ],
                "review_status": review_status,
                "findings": list(job.checkpoint.get("findings", [])),
                "verification": verification if isinstance(verification, dict) else None,
                "promoted_files": list(job.checkpoint.get("promoted_files", [])),
            }

    async def approve_diff(self, job_id: JobId, *, actor_id: str = "user") -> Job:
        async with self._session_factory() as session:
            repositories = _Repositories(session)
            job = await repositories.jobs.get_by_id(job_id)
            if job is None:
                msg = f"Job not found: {job_id}"
                raise ValueError(msg)
            if job.state != JobState.COMPLETED:
                msg = "Job must be completed before diff approval"
                raise ValueError(msg)
            review_status = str(job.checkpoint.get("review_status", "pending"))
            if review_status in {"approved", "rejected", "applied"}:
                msg = f"Diff already {review_status}"
                raise ValueError(msg)
            job = await self._update_checkpoint(repositories, job, review_status="approved")
            await self._record_event(
                repositories,
                job,
                "DIFF_APPROVED",
                {"actor_id": actor_id},
                actor_id,
            )
            return job

    async def reject_diff(
        self,
        job_id: JobId,
        *,
        reason: str = "",
        actor_id: str = "user",
    ) -> Job:
        async with self._session_factory() as session:
            repositories = _Repositories(session)
            job = await repositories.jobs.get_by_id(job_id)
            if job is None:
                msg = f"Job not found: {job_id}"
                raise ValueError(msg)
            if job.state != JobState.COMPLETED:
                msg = "Job must be completed before diff rejection"
                raise ValueError(msg)
            review_status = str(job.checkpoint.get("review_status", "pending"))
            if review_status in {"approved", "rejected", "applied"}:
                msg = f"Diff already {review_status}"
                raise ValueError(msg)
            job = await self._update_checkpoint(
                repositories,
                job,
                review_status="rejected",
                rejection_reason=reason,
            )
            await self._record_event(
                repositories,
                job,
                "DIFF_REJECTED",
                {"actor_id": actor_id, "reason": reason},
                actor_id,
            )
            return job

    async def apply_to_source(self, job_id: JobId, *, actor_id: str = "user") -> dict[str, object]:
        async with self._session_factory() as session:
            repositories = _Repositories(session)
            job = await repositories.jobs.get_by_id(job_id)
            if job is None:
                msg = f"Job not found: {job_id}"
                raise ValueError(msg)
            if str(job.checkpoint.get("review_status")) != "approved":
                msg = "Diff must be approved before apply"
                raise ValueError(msg)
            if job.checkpoint.get("applied_at"):
                msg = "Changes already applied to source"
                raise ValueError(msg)

            workspace_id = _workspace_id_from_job(job)
            if workspace_id is None:
                msg = "Workspace not found for job"
                raise ValueError(msg)

            workspace = await repositories.workspaces.get_by_id(workspace_id)
            project = await repositories.projects.get_by_id(job.project_id)
            if workspace is None or project is None:
                msg = "Workspace or project not found"
                raise ValueError(msg)

            workspace_path = Path(workspace.path)
            source_path = Path(project.source_location)
            diff_text = workspace_diff_text(workspace_path)
            applied_files = [
                str(path)
                for path in job.checkpoint.get("applied_files", [])
                if isinstance(path, str)
            ]
            try:
                promoted = promote_workspace_to_source(
                    workspace_path=workspace_path,
                    source_path=source_path,
                    diff_text=diff_text,
                    file_paths=applied_files or None,
                )
            except PromotionError as exc:
                msg = exc.message
                raise ValueError(msg) from exc

            job = await self._update_checkpoint(
                repositories,
                job,
                review_status="applied",
                promoted_files=promoted,
                applied_at=datetime.now(UTC).isoformat(),
            )
            await self._record_event(
                repositories,
                job,
                "DIFF_APPLIED",
                {"actor_id": actor_id, "promoted_files": promoted},
                actor_id,
            )
            return {
                "job_id": str(job_id),
                "promoted_files": promoted,
                "source_path": str(source_path),
            }

    async def _execute_analyze(self, repositories: _Repositories, job: Job, worker_id: str) -> Job:
        project = await repositories.projects.get_by_id(job.project_id)
        if project is None:
            return await self._fail_job(repositories, job, worker_id, error="Project not found")

        job = await self._transition(
            repositories, job, JobState.PREPARING, "JOB_PREPARING", worker_id
        )
        analysis = ProjectAnalysisService(repositories.session)
        profile = await analysis.analyze(project)
        job = await self._transition(
            repositories, job, JobState.RUNNING, "ANALYSIS_STARTED", worker_id
        )
        await self._record_event(
            repositories,
            job,
            "ANALYSIS_FINISHED",
            {"profile_id": str(profile.id), "symbol_count": profile.symbol_count},
            worker_id,
        )
        return await self._complete_job(
            repositories,
            job,
            worker_id,
            {"profile_id": str(profile.id), "symbol_count": profile.symbol_count},
        )

    async def _execute_implementation(
        self,
        repositories: _Repositories,
        job: Job,
        worker_id: str,
    ) -> Job:
        plan_id_raw = job.payload.get("plan_id")
        if plan_id_raw is None:
            return await self._fail_job(repositories, job, worker_id, error="Missing plan_id")

        plan = await repositories.plans.get_by_id(PlanId.from_string(str(plan_id_raw)))
        if plan is None:
            return await self._fail_job(repositories, job, worker_id, error="Plan not found")

        goal = await repositories.goals.get_by_id(plan.goal_id)
        if goal is None:
            return await self._fail_job(repositories, job, worker_id, error="Goal not found")

        project = await repositories.projects.get_by_id(job.project_id)
        if project is None:
            return await self._fail_job(repositories, job, worker_id, error="Project not found")

        profile = await ProjectAnalysisService(repositories.session).get_latest_profile(project.id)

        job = await self._transition(
            repositories, job, JobState.PREPARING, "JOB_PREPARING", worker_id
        )
        workspace = await self._ensure_workspace(repositories, job, project, worker_id)
        job = await self._update_checkpoint(
            repositories,
            job,
            workspace_id=str(workspace.id),
            review_status="pending",
            applied_files=[],
        )
        job = await self._transition(
            repositories, job, JobState.RUNNING, "IMPLEMENTATION_STARTED", worker_id
        )

        workspace_path = Path(workspace.path)
        context = gather_context_via_tools(workspace_path, goal)
        user_prompt = _build_implementation_prompt(goal, plan, profile, context)

        try:
            completion = await self._model_router.complete(
                system_prompt=IMPLEMENTATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            implementation = parse_implementation_output(completion.content)
            apply_result = apply_implementation(workspace_path, implementation)
            await self._record_event(
                repositories,
                job,
                "PATCH_APPLIED",
                {
                    "files": apply_result.applied_files,
                    "summary": implementation.summary,
                    "model_id": completion.model_id,
                },
                worker_id,
            )
            job = await self._update_checkpoint(
                repositories,
                job,
                applied_files=apply_result.applied_files,
            )
            artifacts = ArtifactStore(self._settings, repositories.session)
            await artifacts.store_text(
                project_id=job.project_id,
                job_id=job.id,
                artifact_type="implementation",
                filename="implementation.json",
                content=json.dumps(
                    {
                        "summary": implementation.summary,
                        "files": apply_result.applied_files,
                        "model_id": completion.model_id,
                    },
                    indent=2,
                ),
            )
        except (ImplementationParseError, PatchEngineError, ToolGatewayError) as exc:
            return await self._fail_job(repositories, job, worker_id, error=str(exc))

        job = await self._transition(
            repositories, job, JobState.VERIFYING, "VERIFICATION_STARTED", worker_id
        )
        verify_profile = await ProjectAnalysisService(repositories.session).get_latest_profile(
            project.id,
        )
        gate_result = await self._run_verification(workspace, verify_profile)
        await self._record_event(
            repositories,
            job,
            "VERIFICATION_FINISHED",
            {"result": gate_result.result.value, "summary": gate_result.summary},
            worker_id,
        )
        job = await self._update_checkpoint(
            repositories,
            job,
            last_verification_result=gate_result.result.value,
            review_status=(
                "ready"
                if gate_result.result == VerificationResult.PASS
                else "needs_review"
            ),
            findings=[{"summary": gate_result.summary}],
            verification=serialize_verification(gate_result),
        )

        if gate_result.result in {VerificationResult.PASS, VerificationResult.PASS_WITH_WARNINGS}:
            return await self._complete_job(
                repositories,
                job,
                worker_id,
                {
                    "verification_result": gate_result.result.value,
                    "workspace_id": str(workspace.id),
                },
            )

        job = await self._transition(
            repositories, job, JobState.REPAIRING, "REPAIR_STARTED", worker_id
        )
        repaired = await self._attempt_repair(
            repositories,
            job,
            workspace,
            goal,
            gate_result.summary,
            worker_id,
        )
        if repaired is None:
            return await self._fail_job(
                repositories,
                job,
                worker_id,
                error="Verification failed and repair was blocked",
                checkpoint_updates={"verification_result": gate_result.result.value},
            )

        job = await self._transition(
            repositories, repaired, JobState.VERIFYING, "VERIFICATION_STARTED", worker_id
        )
        second_gate = await self._run_verification(workspace, verify_profile)
        await self._record_event(
            repositories,
            job,
            "VERIFICATION_FINISHED",
            {"result": second_gate.result.value, "summary": second_gate.summary, "iteration": 1},
            worker_id,
        )
        job = await self._update_checkpoint(
            repositories,
            job,
            last_verification_result=second_gate.result.value,
            review_status=(
                "ready"
                if second_gate.result == VerificationResult.PASS
                else "needs_review"
            ),
            verification=serialize_verification(second_gate),
        )

        if second_gate.result in {VerificationResult.PASS, VerificationResult.PASS_WITH_WARNINGS}:
            return await self._complete_job(
                repositories,
                job,
                worker_id,
                {
                    "verification_result": second_gate.result.value,
                    "workspace_id": str(workspace.id),
                    "repair_iteration": 1,
                },
            )

        return await self._fail_job(
            repositories,
            job,
            worker_id,
            error=second_gate.summary,
            checkpoint_updates={"verification_result": second_gate.result.value},
        )

    async def _attempt_repair(
        self,
        repositories: _Repositories,
        job: Job,
        workspace: Workspace,
        goal: Goal,
        failure_summary: str,
        worker_id: str,
    ) -> Job | None:
        workspace_path = Path(workspace.path)
        context = gather_context_via_tools(workspace_path, goal)
        user_prompt = _build_repair_prompt(goal, failure_summary, context)

        completion = await self._model_router.complete(
            system_prompt=REPAIR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        iteration = int(job.checkpoint.get("repair_iteration", 0))
        iteration_result = self._repair_loop.run_iteration(
            iteration=iteration,
            patch_content=completion.content,
            verification_result=VerificationResult.FAIL_CODE,
            log_excerpt=failure_summary,
        )
        if iteration_result.blocked:
            await self._record_event(
                repositories,
                job,
                "REPAIR_BLOCKED",
                {"reason": iteration_result.block_reason},
                worker_id,
            )
            return None

        try:
            implementation = parse_implementation_output(completion.content)
            apply_implementation(workspace_path, implementation)
        except (ImplementationParseError, PatchEngineError) as exc:
            await self._record_event(
                repositories,
                job,
                "REPAIR_BLOCKED",
                {"reason": str(exc)},
                worker_id,
            )
            return None

        await self._record_event(
            repositories,
            job,
            "REPAIR_ITERATION",
            {
                "iteration": iteration_result.iteration,
                "patch_hash": iteration_result.patch_hash,
            },
            worker_id,
        )
        return await self._update_checkpoint(
            repositories,
            job,
            repair_iteration=iteration + 1,
            repair_hashes=[
                *list(job.checkpoint.get("repair_hashes", [])),
                iteration_result.patch_hash,
            ],
        )

    async def _run_verification(self, workspace: Workspace, profile: ProjectProfile | None):
        workspace_path = Path(workspace.path)
        gateway = ToolGateway.for_workspace(
            workspace_path,
            lease_token=workspace.lease.token if workspace.lease else None,
            expected_lease_token=workspace.lease.token if workspace.lease else None,
            write_allowed=False,
        )
        gate = VerificationGate(gateway)
        return gate.run(matrix_for_workspace(workspace_path, profile))

    async def _ensure_workspace(
        self,
        repositories: _Repositories,
        job: Job,
        project: Project,
        worker_id: str,
    ) -> Workspace:
        existing_id = _workspace_id_from_job(job)
        if existing_id is not None:
            workspace = await repositories.workspaces.get_by_id(existing_id)
            if workspace is not None:
                return workspace

        workspace_id = WorkspaceId.generate()
        workspace = self._workspace_manager.create_workspace(
            workspace_id=workspace_id,
            project_id=project.id,
            source_path=Path(project.source_location),
            job_id=job.id,
            branch=project.default_branch,
            read_only=False,
        )
        workspace = Workspace(
            id=workspace.id,
            project_id=workspace.project_id,
            path=workspace.path,
            strategy=workspace.strategy,
            base_revision=workspace.base_revision,
            branch=workspace.branch,
            state=WorkspaceState.READY,
            lease=workspace.lease,
            file_hashes=workspace.file_hashes,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        saved = await repositories.workspaces.create(workspace, job_id=job.id)
        await self._record_event(
            repositories,
            job,
            "WORKSPACE_CREATED",
            {"workspace_id": str(saved.id), "strategy": saved.strategy.value},
            worker_id,
        )
        return saved

    async def _complete_job(
        self,
        repositories: _Repositories,
        job: Job,
        worker_id: str,
        payload: dict[str, object],
    ) -> Job:
        job = await self._transition(
            repositories, job, JobState.COMPLETED, "JOB_FINISHED", worker_id
        )
        await self._record_event(repositories, job, "JOB_COMPLETED", payload, worker_id)
        return job

    async def _fail_job(
        self,
        repositories: _Repositories,
        job: Job,
        worker_id: str,
        *,
        error: str,
        checkpoint_updates: dict[str, object] | None = None,
    ) -> Job:
        if checkpoint_updates:
            job = await self._update_checkpoint(repositories, job, **checkpoint_updates)
        if can_transition(job.state, JobState.FAILED):
            job = await self._set_state(repositories, job, JobState.FAILED)
        await self._record_event(repositories, job, "JOB_FAILED", {"error": error}, worker_id)
        return job

    async def _transition(
        self,
        repositories: _Repositories,
        job: Job,
        target: JobState,
        event_type: str,
        worker_id: str,
    ) -> Job:
        if not can_transition(job.state, target):
            return job
        updated = await self._set_state(repositories, job, target)
        await self._record_event(
            repositories, updated, event_type, {"state": target.value}, worker_id
        )
        return updated

    async def _set_state(self, repositories: _Repositories, job: Job, state: JobState) -> Job:
        updated = _copy_job(job, state=state)
        return await repositories.jobs.update(updated)

    async def _update_checkpoint(
        self, repositories: _Repositories, job: Job, **fields: object
    ) -> Job:
        checkpoint = dict(job.checkpoint)
        checkpoint.update(fields)
        updated = _copy_job(job, checkpoint=checkpoint)
        return await repositories.jobs.update(updated)

    async def _record_event(
        self,
        repositories: _Repositories,
        job: Job,
        event_type: str,
        payload: dict[str, object],
        worker_id: str,
    ) -> None:
        events = await repositories.evidence.list_for_job(job.id)
        ledger = EvidenceLedger.from_events(events) if events else EvidenceLedger()
        event = ledger.append(
            event_type=event_type,
            payload=payload,
            project_id=job.project_id,
            job_id=job.id,
            actor_type="worker",
            actor_id=worker_id,
        )
        await repositories.evidence.append(event)


class _Repositories:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.jobs = SqlAlchemyJobRepository(session)
        self.projects = SqlAlchemyProjectRepository(session)
        self.plans = SqlAlchemyPlanRepository(session)
        self.goals = SqlAlchemyGoalRepository(session)
        self.workspaces = SqlAlchemyWorkspaceRepository(session)
        self.evidence = SqlAlchemyEvidenceRepository(session)


def _workspace_id_from_job(job: Job) -> WorkspaceId | None:
    raw = job.checkpoint.get("workspace_id") or job.payload.get("workspace_id")
    if raw is None:
        return None
    return WorkspaceId.from_string(str(raw))


def _copy_job(
    job: Job,
    *,
    state: JobState | None = None,
    checkpoint: dict[str, object] | None = None,
) -> Job:
    return Job(
        id=job.id,
        project_id=job.project_id,
        job_type=job.job_type,
        state=state or job.state,
        autonomy_level=job.autonomy_level,
        payload=job.payload,
        worker_id=job.worker_id,
        lease_expires_at=job.lease_expires_at,
        created_at=job.created_at,
        updated_at=datetime.now(UTC),
        checkpoint=checkpoint if checkpoint is not None else job.checkpoint,
        budgets=job.budgets,
    )


def _build_implementation_prompt(
    goal: Goal,
    plan: Plan,
    profile: ProjectProfile | None,
    context: dict[str, str],
) -> str:
    lines = [
        f"Goal: {goal.title}",
        f"Intent: {goal.intent}",
        f"Constraints: {', '.join(goal.constraints) or 'none'}",
        "Plan steps:",
    ]
    for step in plan.steps:
        lines.append(f"- {step.ordinal}. {step.title}: {step.description}")
    if profile:
        lines.append(f"Languages: {', '.join(profile.languages)}")
        lines.append(f"Test commands: {profile.commands.get('test', [])}")
    lines.append("Workspace files:")
    for path, content in context.items():
        lines.append(f"--- {path} ---")
        lines.append(content)
    return "\n".join(lines)


def _build_repair_prompt(
    goal: Goal,
    failure_summary: str,
    context: dict[str, str],
) -> str:
    lines = [
        f"Goal: {goal.title}",
        f"Failure summary: {failure_summary}",
        "Current workspace files:",
    ]
    for path, content in context.items():
        lines.append(f"--- {path} ---")
        lines.append(content)
    return "\n".join(lines)
