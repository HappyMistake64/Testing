"""Structured model output schemas for implementation jobs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FileChangeSchema(BaseModel):
    """Single whole-file change proposed by the model."""

    path: str = Field(min_length=1)
    new_content: str
    reason: str = ""


class ImplementationOutputSchema(BaseModel):
    """Validated structured implementation output."""

    changes: list[FileChangeSchema] = Field(min_length=1)
    summary: str = ""
