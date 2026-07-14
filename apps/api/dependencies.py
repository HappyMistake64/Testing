"""Application dependencies and composition."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fade_agent_runtime.orchestrator import AgentRuntimeOrchestrator
from fade_application.analysis import AnalysisService
from fade_application.jobs import JobService
from fade_application.patches import PatchService
from fade_application.planning import GoalApplicationService, PlanApplicationService
from fade_application.policies import PolicyService
from fade_application.projects import ProjectService
from fade_application.workspaces import WorkspaceService
from fade_infrastructure.database import create_engine, create_session_factory
from fade_infrastructure.evidence_repository import SqlAlchemyEvidenceRepository
from fade_infrastructure.goal_repository import SqlAlchemyGoalRepository
from fade_infrastructure.job_queue import SqlAlchemyJobQueue
from fade_infrastructure.job_repository import SqlAlchemyJobRepository
from fade_infrastructure.path_safety import PathSafetyService
from fade_infrastructure.plan_repository import SqlAlchemyPlanRepository
from fade_infrastructure.policy_repository import SqlAlchemyPolicyRepository
from fade_infrastructure.preflight import PreflightService
from fade_infrastructure.project_analysis_service import ProjectAnalysisService
from fade_infrastructure.project_repository import SqlAlchemyProjectRepository
from fade_infrastructure.settings import Settings
from fade_infrastructure.system_health import SystemHealthService
from fade_infrastructure.workspace_manager import WorkspaceManager
from fade_infrastructure.workspace_repository import SqlAlchemyWorkspaceRepository
from fade_model_router.router import create_default_router
from fade_planning.plan_service import PlanService
from fade_repair_loop.repair_loop import RepairLoop, RepairLoopConfig
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


class AppState:
    """Shared application state attached to FastAPI app."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_engine(settings)
        self.session_factory = create_session_factory(self.engine)
        self.health_service = SystemHealthService(settings, self.session_factory)
        self.path_safety = PathSafetyService(settings)
        self.preflight = PreflightService(settings)
        self.workspace_manager = WorkspaceManager(settings.workspaces_dir)
        self.repair_loop = RepairLoop(RepairLoopConfig())
        self.model_router = create_default_router(
            openai_api_key=(
                settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
            ),
            ollama_base_url=settings.ollama_base_url,
            ollama_default_model=settings.ollama_default_model,
            include_stub=settings.env in {"test", "development"},
        )
        self.plan_service = PlanService(self.model_router)
        self.agent_runtime = AgentRuntimeOrchestrator(
            settings,
            self.session_factory,
            self.model_router,
            repair_loop=self.repair_loop,
        )

    def project_service(self, session: AsyncSession) -> ProjectService:
        return ProjectService(
            repository=SqlAlchemyProjectRepository(session),
            path_safety=self.path_safety,
            preflight=self.preflight,
        )

    def analysis_service(self, session: AsyncSession) -> AnalysisService:
        return AnalysisService(
            projects=SqlAlchemyProjectRepository(session),
            analysis=ProjectAnalysisService(session),
        )

    def job_service(self, session: AsyncSession) -> JobService:
        return JobService(
            repository=SqlAlchemyJobRepository(session),
            evidence=SqlAlchemyEvidenceRepository(session),
            workspace_repository=SqlAlchemyWorkspaceRepository(session),
            repair_loop=self.repair_loop,
        )

    def workspace_service(self, session: AsyncSession) -> WorkspaceService:
        return WorkspaceService(
            workspace_manager=self.workspace_manager,
            project_repository=SqlAlchemyProjectRepository(session),
            workspace_repository=SqlAlchemyWorkspaceRepository(session),
            job_repository=SqlAlchemyJobRepository(session),
        )

    def patch_service(self, session: AsyncSession) -> PatchService:
        return PatchService(SqlAlchemyWorkspaceRepository(session))

    def policy_service(self, session: AsyncSession) -> PolicyService:
        return PolicyService(SqlAlchemyPolicyRepository(session))

    def job_queue(self, session: AsyncSession) -> SqlAlchemyJobQueue:
        return SqlAlchemyJobQueue(session, SqlAlchemyJobRepository(session))

    def goal_service(self, session: AsyncSession) -> GoalApplicationService:
        return GoalApplicationService(
            goals=SqlAlchemyGoalRepository(session),
            projects=SqlAlchemyProjectRepository(session),
        )

    def plan_application_service(self, session: AsyncSession) -> PlanApplicationService:
        return PlanApplicationService(
            plans=SqlAlchemyPlanRepository(session),
            goals=SqlAlchemyGoalRepository(session),
            analysis=ProjectAnalysisService(session),
            plan_service=self.plan_service,
        )

    async def shutdown(self) -> None:
        await self.engine.dispose()


def get_app_state(request: Request) -> AppState:
    return request.app.state.fade  # type: ignore[attr-defined]


def get_agent_runtime(
    state: Annotated[AppState, Depends(get_app_state)],
) -> AgentRuntimeOrchestrator:
    return state.agent_runtime


async def get_db_session(
    state: Annotated[AppState, Depends(get_app_state)],
) -> AsyncGenerator[AsyncSession, None]:
    async with state.session_factory() as session:
        yield session


def get_health_service(
    state: Annotated[AppState, Depends(get_app_state)],
) -> SystemHealthService:
    return state.health_service


async def get_project_service(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectService:
    return state.project_service(session)


async def get_analysis_service(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalysisService:
    return state.analysis_service(session)


async def get_job_service(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobService:
    return state.job_service(session)


async def get_goal_service(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GoalApplicationService:
    return state.goal_service(session)


async def get_plan_service(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlanApplicationService:
    return state.plan_application_service(session)


async def get_policy_service(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PolicyService:
    return state.policy_service(session)


async def get_workspace_service(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceService:
    return state.workspace_service(session)


async def get_patch_service(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PatchService:
    return state.patch_service(session)
