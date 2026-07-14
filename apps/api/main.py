"""FastAPI composition root."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apps.api.dependencies import AppState
from apps.api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from apps.api.middleware import CorrelationIdMiddleware
from apps.api.routers import goals, jobs, patches, plans, policies, projects, system, workspaces
from fade_infrastructure.logging import configure_logging, get_logger
from fade_infrastructure.settings import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    app.state.fade = AppState(settings)  # type: ignore[attr-defined]
    logger.info("fade_starting", version=settings.version, env=settings.env)
    yield
    await app.state.fade.shutdown()  # type: ignore[attr-defined]
    logger.info("fade_stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="FADE Platform",
        description="First Artificial David's Ecosystem",
        version=settings.version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]
    from starlette.exceptions import HTTPException

    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]

    app.include_router(system.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(goals.router, prefix="/api/v1")
    app.include_router(plans.router, prefix="/api/v1")
    app.include_router(workspaces.router, prefix="/api/v1")
    app.include_router(patches.router, prefix="/api/v1")
    app.include_router(policies.router, prefix="/api/v1")

    return app


app = create_app()
