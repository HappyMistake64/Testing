"""Application port interfaces (dependency inversion)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    """Database connectivity health snapshot."""

    connected: bool
    engine: str
    wal_mode: bool | None = None
    integrity_ok: bool | None = None
    project_count: int | None = None


@dataclass(frozen=True, slots=True)
class SystemHealthSnapshot:
    """Aggregated system health for doctor/health endpoints."""

    status: str
    version: str
    environment: str
    database: DatabaseHealth
    capabilities: dict[str, bool]


class SystemHealthPort(ABC):
    """Port for system health checks."""

    @abstractmethod
    async def check_health(self) -> SystemHealthSnapshot:
        """Return current system health snapshot."""


class ProjectRepositoryPort(ABC):
    """Port for project persistence (Milestone 1+)."""

    @abstractmethod
    async def count(self) -> int:
        """Return number of registered projects."""

    @abstractmethod
    async def exists_table(self) -> bool:
        """Return whether projects table is accessible."""
