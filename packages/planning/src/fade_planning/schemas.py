"""Pydantic schemas for structured plan output."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fade_domain.types import RiskLevel


class PlanStepSchema(BaseModel):
    ordinal: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    step_type: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(default_factory=list)


class PlanOutputSchema(BaseModel):
    """Validated structured plan from model output."""

    assumptions: list[str] = Field(default_factory=list)
    steps: list[PlanStepSchema] = Field(min_length=1)
    test_plan: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
