"""Application dependencies and composition."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fade_infrastructure.database import create_engine, create_session_factory
from fade_infrastructure.settings import Settings
from fade_infrastructure.system_health import SystemHealthService
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


class AppState:
    """Shared application state attached to FastAPI app."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_engine(settings)
        self.session_factory = create_session_factory(self.engine)
        self.health_service = SystemHealthService(settings, self.session_factory)

    async def shutdown(self) -> None:
        await self.engine.dispose()


def get_app_state(request: Request) -> AppState:
    return request.app.state.fade  # type: ignore[attr-defined]


async def get_db_session(
    state: Annotated[AppState, Depends(get_app_state)],
) -> AsyncGenerator[AsyncSession, None]:
    async with state.session_factory() as session:
        yield session


def get_health_service(
    state: Annotated[AppState, Depends(get_app_state)],
) -> SystemHealthService:
    return state.health_service
