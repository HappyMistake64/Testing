"""Project analysis profile domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from fade_domain.ids import ProfileId, ProjectId


@dataclass(frozen=True, slots=True)
class SymbolEntry:
    """Indexed symbol from source code analysis."""

    name: str
    kind: str
    file_path: str
    line: int
    language: str
    content_hash: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectProfile:
    """Verified analysis result for a registered project."""

    id: ProfileId
    project_id: ProjectId
    version: int
    revision: str | None
    languages: list[str]
    frameworks: list[str]
    manifests: list[str]
    commands: dict[str, list[str]]
    architecture_summary: str | None
    risk_flags: list[str]
    symbol_count: int
    created_at: datetime
    symbols: list[SymbolEntry] = field(default_factory=list)
