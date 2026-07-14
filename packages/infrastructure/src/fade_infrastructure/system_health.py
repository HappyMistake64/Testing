"""System health adapter implementing application port."""

from __future__ import annotations

from fade_application.ports import DatabaseHealth, SystemHealthPort, SystemHealthSnapshot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fade_infrastructure.database import check_database_health
from fade_infrastructure.settings import Settings


class SystemHealthService(SystemHealthPort):
    """Infrastructure implementation of system health checks."""

    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory

    async def check_health(self) -> SystemHealthSnapshot:
        async with self._session_factory() as session:
            db_raw = await check_database_health(session)

        db_health = DatabaseHealth(
            connected=bool(db_raw.get("connected")),
            engine="sqlite",
            wal_mode=db_raw.get("wal_mode"),  # type: ignore[arg-type]
            integrity_ok=db_raw.get("integrity_ok"),  # type: ignore[arg-type]
            project_count=db_raw.get("project_count"),  # type: ignore[arg-type]
        )

        all_ok = db_health.connected and db_health.integrity_ok is not False
        status = "healthy" if all_ok else "degraded"

        capabilities = {
            "project_registry": True,
            "project_analysis": True,
            "agent_runtime": False,
            "tool_gateway": False,
            "model_router": True,
            "evidence_ledger": True,
            "job_queue": True,
            "workspace_isolation": False,
        }

        return SystemHealthSnapshot(
            status=status,
            version=self._settings.version,
            environment=self._settings.env,
            database=db_health,
            capabilities=capabilities,
        )

    async def check_doctor(self) -> dict[str, object]:
        """Extended diagnostics for doctor endpoint."""
        issues: list[dict[str, str]] = []
        checks: dict[str, object] = {}

        async with self._session_factory() as session:
            db_raw = await check_database_health(session)

        checks["database"] = db_raw

        if not db_raw.get("connected"):
            issues.append({
                "severity": "error",
                "code": "DATABASE_UNAVAILABLE",
                "message": "Cannot connect to database",
            })
        elif db_raw.get("integrity_ok") is False:
            issues.append({
                "severity": "error",
                "code": "DATABASE_INTEGRITY",
                "message": "SQLite integrity check failed",
            })
        elif db_raw.get("wal_mode") is False:
            issues.append({
                "severity": "warning",
                "code": "DATABASE_WAL",
                "message": "SQLite WAL mode is not enabled",
            })

        db_path = self._settings.db_path
        checks["var_directory"] = {
            "path": str(db_path.parent),
            "exists": db_path.parent.exists(),
            "writable": db_path.parent.exists() and db_path.parent.is_dir(),
        }

        if not db_path.parent.exists():
            issues.append({
                "severity": "warning",
                "code": "VAR_DIR_MISSING",
                "message": f"Runtime directory {db_path.parent} does not exist",
            })

        blocking = any(i["severity"] == "error" for i in issues)

        return {
            "status": "fail" if blocking else ("warn" if issues else "pass"),
            "version": self._settings.version,
            "environment": self._settings.env,
            "settings": self._settings.redacted_dict(),
            "checks": checks,
            "issues": issues,
            "capabilities": {
                "project_registry": True,
                "project_analysis": True,
                "agent_runtime": False,
                "tool_gateway": False,
                "model_router": True,
                "evidence_ledger": True,
                "job_queue": True,
            },
        }
