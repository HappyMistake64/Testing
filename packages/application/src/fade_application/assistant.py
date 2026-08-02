"""Assistant application service: sessions, turns, approvals, automations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fade_domain.assistant import (
    AssistantSession,
    AssistantTurn,
    CommandMode,
    MemoryItem,
    TurnState,
)
from fade_domain.ids import (
    ApprovalId,
    AssistantSessionId,
    AssistantTurnId,
    JobId,
    MemoryId,
    ProjectId,
)
from fade_domain.job import Job, JobState
from fade_domain.project import Project, ProjectStatus, SourceType
from fade_domain.types import AutonomyLevel
from fade_infrastructure.assistant_repository import SqlAlchemyAssistantRepository
from fade_infrastructure.automation_repository import (
    Automation,
    SqlAlchemyAutomationRepository,
)
from fade_infrastructure.job_repository import SqlAlchemyJobRepository
from fade_infrastructure.memory_repository import SqlAlchemyMemoryRepository
from fade_infrastructure.project_repository import SqlAlchemyProjectRepository

ASSISTANT_PROJECT_SLUG = "fade-assistant-core"


class AssistantService:
    """Application service for the command-driven assistant."""

    def __init__(
        self,
        *,
        repository: SqlAlchemyAssistantRepository,
        memory: SqlAlchemyMemoryRepository,
        jobs: SqlAlchemyJobRepository,
        projects: SqlAlchemyProjectRepository,
        automations: SqlAlchemyAutomationRepository,
    ) -> None:
        self._repository = repository
        self._memory = memory
        self._jobs = jobs
        self._projects = projects
        self._automations = automations

    # Sessions -----------------------------------------------------------

    async def create_session(
        self,
        *,
        title: str = "",
        provider_id: str | None = None,
        model_id: str | None = None,
    ) -> AssistantSession:
        now = datetime.now(UTC)
        session = AssistantSession(
            id=AssistantSessionId.generate(),
            title=title or f"Session {now:%Y-%m-%d %H:%M}",
            provider_id=provider_id,
            model_id=model_id,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.create_session(session)

    async def list_sessions(self) -> list[AssistantSession]:
        return await self._repository.list_sessions()

    async def get_session(self, session_id: AssistantSessionId) -> AssistantSession | None:
        return await self._repository.get_session(session_id)

    # Turns ----------------------------------------------------------------

    async def create_turn(
        self,
        session_id: AssistantSessionId,
        *,
        command: str,
        mode: CommandMode = CommandMode.EXECUTE,
        provider_id: str | None = None,
        model_id: str | None = None,
    ) -> AssistantTurn:
        session = await self._repository.get_session(session_id)
        if session is None:
            msg = f"Session not found: {session_id}"
            raise ValueError(msg)

        project = await self._ensure_system_project()
        now = datetime.now(UTC)
        job = Job(
            id=JobId.generate(),
            project_id=project.id,
            job_type="assistant_turn",
            state=JobState.QUEUED,
            autonomy_level=AutonomyLevel.ASSISTED,
            payload={"command": command[:2000], "mode": mode.value},
            worker_id=None,
            lease_expires_at=None,
            created_at=now,
            updated_at=now,
        )
        turn = AssistantTurn(
            id=AssistantTurnId.generate(),
            session_id=session_id,
            command=command,
            mode=mode,
            state=TurnState.QUEUED,
            provider_id=provider_id or session.provider_id,
            model_id=model_id or session.model_id,
            response=None,
            created_at=now,
            updated_at=now,
        )
        job = Job(
            id=job.id,
            project_id=job.project_id,
            job_type=job.job_type,
            state=job.state,
            autonomy_level=job.autonomy_level,
            payload={**job.payload, "turn_id": str(turn.id)},
            worker_id=None,
            lease_expires_at=None,
            created_at=now,
            updated_at=now,
        )
        await self._jobs.create(job)
        return await self._repository.create_turn(turn, job_id=str(job.id))

    async def get_turn(self, turn_id: AssistantTurnId) -> AssistantTurn | None:
        return await self._repository.get_turn(turn_id)

    async def list_turns(self, session_id: AssistantSessionId) -> list[AssistantTurn]:
        return await self._repository.list_turns(session_id)

    async def requeue_turn(self, turn_id: AssistantTurnId) -> AssistantTurn | None:
        """After an approval, mark the turn queued so a worker resumes it."""
        turn = await self._repository.get_turn(turn_id)
        if turn is None or turn.state != TurnState.AWAITING_APPROVAL:
            return None
        job_id_raw = await self._repository.get_turn_job_id(turn_id)
        if job_id_raw:
            job = await self._jobs.get_by_id(JobId.from_string(job_id_raw))
            if job is not None and job.state == JobState.BLOCKED:
                now = datetime.now(UTC)
                await self._jobs.update(
                    Job(
                        id=job.id,
                        project_id=job.project_id,
                        job_type=job.job_type,
                        state=JobState.QUEUED,
                        autonomy_level=job.autonomy_level,
                        payload=job.payload,
                        worker_id=None,
                        lease_expires_at=None,
                        created_at=job.created_at,
                        updated_at=now,
                        checkpoint=job.checkpoint,
                        budgets=job.budgets,
                    )
                )
        return await self._repository.update_turn(turn_id, state=TurnState.QUEUED)

    async def ensure_automation_session(self) -> AssistantSession:
        for session in await self._repository.list_sessions():
            if session.title == "Automations":
                return session
        return await self.create_session(title="Automations")

    # Approvals --------------------------------------------------------------

    async def list_pending_approvals(self) -> list[dict[str, object]]:
        return await self._repository.list_pending_approvals()

    async def decide_approval(
        self, approval_id: ApprovalId, *, approve: bool
    ) -> dict[str, object] | None:
        decision = "approved" if approve else "denied"
        approval = await self._repository.decide_approval(approval_id, decision=decision)
        if approval is None:
            return None
        requeued = False
        if approve:
            requeued = await self.requeue_turn(approval.turn_id) is not None
        else:
            await self._repository.update_turn(
                approval.turn_id,
                state=TurnState.FAILED,
                response=f"Approval denied for {approval.tool_name}.",
            )
        return {
            "approval_id": str(approval.id),
            "turn_id": str(approval.turn_id),
            "decision": decision,
            "turn_requeued": requeued,
        }

    # Emergency stop ------------------------------------------------------

    async def emergency_stop(self, *, paused: bool, reason: str | None = None) -> dict[str, object]:
        await self._repository.set_paused(paused, reason=reason)
        revoked = await self._repository.revoke_pending_approvals() if paused else 0
        return {"paused": paused, "revoked_approvals": revoked}

    async def is_paused(self) -> bool:
        return await self._repository.is_paused()

    # Memory ---------------------------------------------------------------

    async def store_memory(self, content: str) -> MemoryItem:
        item = MemoryItem(
            id=MemoryId.generate(),
            content=content,
            source_turn_id=None,
            confidence="user_stated",
            evidence_refs=[],
            expires_at=None,
            created_at=datetime.now(UTC),
        )
        return await self._memory.store(item)

    async def search_memory(self, query: str) -> list[MemoryItem]:
        return await self._memory.search(query)

    async def list_memory(self) -> list[MemoryItem]:
        return await self._memory.list_all()

    async def delete_memory(self, memory_id: MemoryId) -> bool:
        return await self._memory.delete(memory_id)

    # Automations -----------------------------------------------------------

    async def create_automation(
        self,
        *,
        name: str,
        command: str,
        schedule_kind: str,
        interval_seconds: int | None = None,
        delay_seconds: int | None = None,
    ) -> Automation:
        if schedule_kind not in {"once", "interval"}:
            msg = f"Unsupported schedule kind: {schedule_kind}"
            raise ValueError(msg)
        if schedule_kind == "interval" and (not interval_seconds or interval_seconds < 30):
            msg = "Interval automations require interval_seconds >= 30"
            raise ValueError(msg)
        next_run = datetime.now(UTC) + timedelta(seconds=delay_seconds or interval_seconds or 0)
        return await self._automations.create(
            name=name,
            command=command,
            schedule_kind=schedule_kind,
            interval_seconds=interval_seconds,
            next_run_at=next_run,
        )

    async def list_automations(self) -> list[Automation]:
        return await self._automations.list_all()

    async def set_automation_enabled(self, automation_id: str, enabled: bool) -> Automation | None:
        return await self._automations.set_enabled(automation_id, enabled)

    async def delete_automation(self, automation_id: str) -> bool:
        return await self._automations.delete(automation_id)

    # System project ---------------------------------------------------------

    async def _ensure_system_project(self) -> Project:
        existing = await self._projects.get_by_source_location("internal://assistant")
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        project = Project(
            id=ProjectId.generate(),
            name="FADE Assistant Core",
            slug=ASSISTANT_PROJECT_SLUG,
            status=ProjectStatus.READY,
            source_type=SourceType.LOCAL_PATH,
            source_location="internal://assistant",
            default_branch=None,
            tags=["internal", "assistant"],
            preflight_report=None,
            created_at=now,
            updated_at=now,
        )
        return await self._projects.create(project)
