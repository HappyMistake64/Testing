"""Verification matrix builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class VerificationLayer(StrEnum):
    SYNTAX = "syntax"
    STATIC = "static"
    UNIT = "unit"
    INTEGRATION = "integration"
    BUILD = "build"
    SECURITY = "security"


@dataclass(frozen=True, slots=True)
class VerificationCheck:
    """A single verification command."""

    name: str
    layer: VerificationLayer
    argv: list[str]
    required: bool = True
    timeout_s: int = 120
    env: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class VerificationMatrix:
    """Ordered list of checks for a workspace."""

    checks: list[VerificationCheck] = field(default_factory=list)

    @classmethod
    def for_python_project(cls, *, include_build: bool = False) -> VerificationMatrix:
        checks = [
            VerificationCheck(
                name="ruff-check",
                layer=VerificationLayer.SYNTAX,
                argv=["ruff", "check", "."],
            ),
            VerificationCheck(
                name="pytest",
                layer=VerificationLayer.UNIT,
                argv=["pytest", "-q"],
            ),
        ]
        if include_build:
            checks.append(
                VerificationCheck(
                    name="build",
                    layer=VerificationLayer.BUILD,
                    argv=["python", "-m", "build"],
                    required=False,
                ),
            )
        return cls(checks=checks)

    @classmethod
    def minimal(cls) -> VerificationMatrix:
        return cls(
            checks=[
                VerificationCheck(
                    name="python-syntax",
                    layer=VerificationLayer.SYNTAX,
                    argv=["python", "-c", "import sys; sys.exit(0)"],
                    required=True,
                ),
            ],
        )


class VerificationResult(StrEnum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL_CODE = "fail_code"
    FAIL_ENVIRONMENT = "fail_environment"
    FAIL_FLAKY = "fail_flaky"
    BLOCKED_POLICY = "blocked_policy"
    INCONCLUSIVE = "inconclusive"
