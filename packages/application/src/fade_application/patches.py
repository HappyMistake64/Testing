"""Patch application service."""

from __future__ import annotations

from pathlib import Path

from fade_domain.ids import WorkspaceId
from fade_infrastructure.workspace_repository import SqlAlchemyWorkspaceRepository
from fade_patch_engine.patch import ApplyPatchResult, PatchEngine, PatchEngineError, PatchHunk
from fade_tool_gateway.gateway import ToolGateway


class PatchService:
    """Applies patches to leased workspaces."""

    def __init__(self, workspace_repository: SqlAlchemyWorkspaceRepository) -> None:
        self._workspaces = workspace_repository

    async def apply_patch(
        self,
        workspace_id: WorkspaceId,
        *,
        hunks: list[PatchHunk],
        lease_token: str,
    ) -> ApplyPatchResult:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise PatchEngineError("WORKSPACE_NOT_FOUND", "Workspace not found")
        if workspace.lease is None or workspace.lease.token != lease_token:
            raise PatchEngineError("LEASE_INVALID", "Invalid lease token")

        gateway = ToolGateway.for_workspace(
            Path(workspace.path),
            lease_token=lease_token,
            expected_lease_token=workspace.lease.token,
            write_allowed=True,
        )
        for hunk in hunks:
            check = gateway._policy.check_write_path(hunk.path)  # noqa: SLF001
            if check.decision.value == "deny":
                raise PatchEngineError("POLICY_DENIED", check.reason)

        engine = PatchEngine(Path(workspace.path))
        return engine.apply_hunks(hunks)
