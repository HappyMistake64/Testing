"""Diagnosis schema for repair loop."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FailureClass(StrEnum):
    CODE = "code"
    TEST = "test"
    ENVIRONMENT = "environment"
    FLAKY = "flaky"
    POLICY = "policy"
    UNKNOWN = "unknown"


class Hypothesis(BaseModel):
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)


class Diagnosis(BaseModel):
    failure_class: FailureClass
    summary: str
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    relevant_log_excerpt: str = ""
    suggested_actions: list[str] = Field(default_factory=list)
    verification_result: str | None = None
