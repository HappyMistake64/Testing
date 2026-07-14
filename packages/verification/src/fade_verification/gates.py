"""Verification gates - aggregate check results into pass/fail."""

from __future__ import annotations

from dataclasses import dataclass, field

from fade_tool_gateway.gateway import ToolGateway, ToolGatewayError

from fade_verification.result_parsers import (
    CheckResult,
    CheckStatus,
    parse_pytest_output,
    parse_ruff_output,
)
from fade_verification.verification_matrix import (
    VerificationCheck,
    VerificationMatrix,
    VerificationResult,
)


@dataclass(frozen=True, slots=True)
class CheckExecution:
    check: VerificationCheck
    exit_code: int
    stdout: str
    stderr: str
    parsed: CheckResult | None = None
    blocked: bool = False
    block_reason: str | None = None


@dataclass(frozen=True, slots=True)
class VerificationGateResult:
    result: VerificationResult
    executions: list[CheckExecution] = field(default_factory=list)
    summary: str = ""


class VerificationGate:
    """Runs verification matrix and classifies outcome."""

    def __init__(self, gateway: ToolGateway) -> None:
        self._gateway = gateway

    def run(self, matrix: VerificationMatrix) -> VerificationGateResult:
        executions: list[CheckExecution] = []
        has_failure = False
        has_warning = False
        blocked = False

        for check in matrix.checks:
            execution = self._run_check(check)
            executions.append(execution)

            if execution.blocked:
                blocked = True
                if check.required:
                    return VerificationGateResult(
                        result=VerificationResult.BLOCKED_POLICY,
                        executions=executions,
                        summary=execution.block_reason or "Policy blocked check",
                    )
                continue

            if execution.exit_code != 0 or (
                execution.parsed and execution.parsed.status == CheckStatus.FAIL
            ):
                if check.required:
                    has_failure = True
                else:
                    has_warning = True

        if blocked and not has_failure:
            return VerificationGateResult(
                result=VerificationResult.BLOCKED_POLICY,
                executions=executions,
                summary="One or more checks blocked by policy",
            )
        if has_failure:
            return VerificationGateResult(
                result=VerificationResult.FAIL_CODE,
                executions=executions,
                summary="Required verification checks failed",
            )
        if has_warning:
            return VerificationGateResult(
                result=VerificationResult.PASS_WITH_WARNINGS,
                executions=executions,
                summary="Passed with optional check warnings",
            )
        return VerificationGateResult(
            result=VerificationResult.PASS,
            executions=executions,
            summary="All required checks passed",
        )

    def _run_check(self, check: VerificationCheck) -> CheckExecution:
        try:
            result = self._gateway.safe_run_command(
                check.argv,
                timeout_s=check.timeout_s,
                env=check.env,
            )
        except ToolGatewayError as exc:
            return CheckExecution(
                check=check,
                exit_code=-1,
                stdout="",
                stderr=exc.message,
                blocked=True,
                block_reason=exc.message,
            )

        parsed: CheckResult | None = None
        if check.name.startswith("test") or "pytest" in check.argv:
            parsed = parse_pytest_output(result.stdout + result.stderr)
        elif "ruff" in check.argv[0]:
            parsed = parse_ruff_output(result.stdout + result.stderr)

        return CheckExecution(
            check=check,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            parsed=parsed,
        )
