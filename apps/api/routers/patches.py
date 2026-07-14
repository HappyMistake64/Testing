"""Patch API routes."""

from __future__ import annotations

from typing import Annotated

from apps.api.dependencies import get_patch_service
from fade_application.patches import PatchService
from fade_domain.ids import WorkspaceId
from fade_patch_engine.patch import FileOperation, PatchEngineError, PatchHunk, file_hash
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/workspaces", tags=["patches"])


class FileOperationRequest(BaseModel):
    path: str
    new_content: str
    base_hash: str | None = None


class ApplyPatchRequest(BaseModel):
    lease_token: str
    operations: list[FileOperationRequest] = Field(min_length=1)


class ApplyPatchResponse(BaseModel):
    applied_files: list[str]
    skipped_files: list[str]
    new_hashes: dict[str, str]


@router.post("/{workspace_id}/patch", response_model=ApplyPatchResponse)
async def apply_patch(
    workspace_id: str,
    body: ApplyPatchRequest,
    service: Annotated[PatchService, Depends(get_patch_service)],
) -> ApplyPatchResponse:
    hunks: list[PatchHunk] = []
    for op in body.operations:
        base_hash = op.base_hash if op.base_hash is not None else file_hash("")
        hunks.append(
            PatchHunk(
                path=op.path,
                base_hash=base_hash,
                operations=[
                    FileOperation(path=op.path, old_content=None, new_content=op.new_content),
                ],
            ),
        )
    try:
        result = await service.apply_patch(
            WorkspaceId.from_string(workspace_id),
            hunks=hunks,
            lease_token=body.lease_token,
        )
    except PatchEngineError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return ApplyPatchResponse(
        applied_files=result.applied_files,
        skipped_files=result.skipped_files,
        new_hashes=result.new_hashes,
    )
