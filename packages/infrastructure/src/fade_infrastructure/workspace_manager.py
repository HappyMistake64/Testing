"""Workspace manager using git worktree with filesystem copy fallback."""

from __future__ import annotations

import hashlib
import secrets
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fade_domain.ids import JobId, ProjectId, WorkspaceId
from fade_domain.workspace import Workspace, WorkspaceLease, WorkspaceState, WorkspaceStrategy
from fade_patch_engine.patch import file_hash
from fade_tool_gateway.git_ops import git_rev_parse, git_worktree_add, git_worktree_remove


class WorkspaceManagerError(Exception):
    """Raised when workspace operations fail."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class WorkspaceManager:
    """Creates and manages isolated workspaces."""

    def __init__(self, workspaces_root: Path, *, lease_ttl_seconds: int = 3600) -> None:
        self._root = workspaces_root
        self._root.mkdir(parents=True, exist_ok=True)
        self._lease_ttl_seconds = lease_ttl_seconds

    def create_workspace(
        self,
        *,
        workspace_id: WorkspaceId,
        project_id: ProjectId,
        source_path: Path,
        job_id: JobId,
        branch: str | None = None,
        read_only: bool = False,
    ) -> Workspace:
        dest = self._root / str(project_id) / str(workspace_id)
        dest.parent.mkdir(parents=True, exist_ok=True)

        strategy: WorkspaceStrategy
        base_revision: str | None = None

        if read_only:
            workspace_path = self._copy_tree(source_path, dest / "repo")
            strategy = WorkspaceStrategy.FILESYSTEM_COPY
        elif self._is_git_repo(source_path):
            strategy, workspace_path, base_revision = self._create_git_worktree(
                source_path,
                dest,
                branch,
            )
        else:
            workspace_path = self._copy_tree(source_path, dest / "repo")
            strategy = WorkspaceStrategy.FILESYSTEM_COPY
            base_revision = self._directory_fingerprint(workspace_path)

        now = datetime.now(UTC)
        file_hashes = self._compute_file_hashes(workspace_path)
        lease = self._create_lease(job_id)

        return Workspace(
            id=workspace_id,
            project_id=project_id,
            path=str(workspace_path),
            strategy=strategy,
            base_revision=base_revision,
            branch=branch,
            state=WorkspaceState.LEASED,
            lease=lease,
            file_hashes=file_hashes,
            created_at=now,
            updated_at=now,
        )

    def release_workspace(self, workspace: Workspace) -> Workspace:
        return Workspace(
            id=workspace.id,
            project_id=workspace.project_id,
            path=workspace.path,
            strategy=workspace.strategy,
            base_revision=workspace.base_revision,
            branch=workspace.branch,
            state=WorkspaceState.RELEASED,
            lease=None,
            file_hashes=workspace.file_hashes,
            created_at=workspace.created_at,
            updated_at=datetime.now(UTC),
        )

    def validate_lease(self, workspace: Workspace, token: str | None) -> bool:
        if workspace.lease is None:
            return False
        if workspace.lease.token != token:
            return False
        return workspace.lease.expires_at > datetime.now(UTC)

    def cleanup_workspace(self, workspace: Workspace, *, source_path: Path | None = None) -> None:
        path = Path(workspace.path)
        worktree_root = path.parent if path.name == "repo" else path
        if not worktree_root.exists():
            return
        if workspace.strategy == WorkspaceStrategy.GIT_WORKTREE and source_path is not None:
            git_worktree_remove(source_path, path)
        else:
            shutil.rmtree(worktree_root, ignore_errors=True)

    def _create_git_worktree(
        self,
        source_path: Path,
        dest: Path,
        branch: str | None,
    ) -> tuple[WorkspaceStrategy, Path, str | None]:
        worktree_path = dest / "repo"
        worktree_branch = branch or f"fade-ws-{secrets.token_hex(4)}"
        try:
            result = git_worktree_add(source_path, worktree_path, worktree_branch)
            if result.base_revision is None and result.stderr:
                raise WorkspaceManagerError("WORKTREE_FAILED", result.stderr)
            return WorkspaceStrategy.GIT_WORKTREE, worktree_path, result.base_revision
        except (WorkspaceManagerError, OSError):
            workspace_path = self._copy_tree(source_path, worktree_path)
            return WorkspaceStrategy.FILESYSTEM_COPY, workspace_path, self._directory_fingerprint(
                workspace_path,
            )

    def _copy_tree(self, source_path: Path, dest: Path) -> Path:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(
            source_path,
            dest,
            ignore=shutil.ignore_patterns(".git"),
            dirs_exist_ok=True,
        )
        return dest

    def _create_lease(self, job_id: JobId) -> WorkspaceLease:
        return WorkspaceLease(
            token=secrets.token_urlsafe(32),
            job_id=job_id,
            expires_at=datetime.now(UTC) + timedelta(seconds=self._lease_ttl_seconds),
        )

    def _is_git_repo(self, path: Path) -> bool:
        return (path / ".git").exists()

    def _directory_fingerprint(self, path: Path) -> str:
        digest = hashlib.sha256()
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file() and ".git" not in file_path.parts:
                rel = str(file_path.relative_to(path)).encode()
                digest.update(rel)
                digest.update(file_path.read_bytes())
        return digest.hexdigest()

    def _compute_file_hashes(self, workspace_path: Path) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for file_path in workspace_path.rglob("*"):
            if file_path.is_file() and ".git" not in file_path.parts:
                rel = str(file_path.relative_to(workspace_path))
                hashes[rel] = file_hash(
                    file_path.read_text(encoding="utf-8", errors="replace"),
                )
        return hashes
