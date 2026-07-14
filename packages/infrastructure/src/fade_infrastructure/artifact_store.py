"""Filesystem artifact store."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fade_domain.ids import ArtifactId, JobId, ProjectId
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from fade_infrastructure.models import ArtifactModel
from fade_infrastructure.settings import Settings


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    id: ArtifactId
    project_id: ProjectId
    job_id: JobId | None
    artifact_type: str
    path: str
    sha256: str
    size_bytes: int
    metadata: dict[str, object]
    created_at: datetime


class ArtifactStore:
    """Store artifact files on disk with DB references."""

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._settings = settings
        self._session = session
        self._root = settings.var_dir / "artifacts"

    def _project_dir(self, project_id: ProjectId) -> Path:
        path = self._root / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def store_text(
        self,
        *,
        project_id: ProjectId,
        job_id: JobId | None,
        artifact_type: str,
        filename: str,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> StoredArtifact:
        directory = self._project_dir(project_id)
        if job_id:
            directory = directory / str(job_id)
            directory.mkdir(parents=True, exist_ok=True)
        file_path = directory / filename
        file_path.write_text(content, encoding="utf-8")
        data = content.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        now = datetime.now(UTC)
        artifact_id = ArtifactId(str(ULID()))
        model = ArtifactModel(
            id=artifact_id,
            project_id=str(project_id),
            job_id=str(job_id) if job_id else None,
            artifact_type=artifact_type,
            path=str(file_path),
            sha256=digest,
            size_bytes=len(data),
            metadata_json=json.dumps(metadata or {}),
            created_at=now,
        )
        self._session.add(model)
        await self._session.commit()
        return StoredArtifact(
            id=artifact_id,
            project_id=project_id,
            job_id=job_id,
            artifact_type=artifact_type,
            path=str(file_path),
            sha256=digest,
            size_bytes=len(data),
            metadata=metadata or {},
            created_at=now,
        )
