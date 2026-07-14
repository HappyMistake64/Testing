"""Domain value types and enumerations."""

from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    """Assessed risk level for operations or plans."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_string(cls, value: str) -> RiskLevel:
        try:
            return cls(value.lower())
        except ValueError as exc:
            msg = f"Invalid RiskLevel: {value!r}"
            raise ValueError(msg) from exc


class AutonomyLevel(StrEnum):
    """Degree of autonomy granted to FADE for a job or project."""

    READ_ONLY = "read_only"
    PLAN = "plan"
    ASSISTED = "assisted"
    SUPERVISED = "supervised"
    AUTONOMOUS = "autonomous"

    @classmethod
    def from_string(cls, value: str) -> AutonomyLevel:
        try:
            return cls(value.lower())
        except ValueError as exc:
            msg = f"Invalid AutonomyLevel: {value!r}"
            raise ValueError(msg) from exc


class ErrorCode(StrEnum):
    """Stable machine-readable error codes for API responses."""

    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
