"""Parse verification command output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Parsed result of a single check."""

    name: str
    status: CheckStatus
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    messages: list[str] = field(default_factory=list)


def parse_pytest_output(output: str) -> CheckResult:
    passed = failed = skipped = errors = 0
    summary = re.search(
        r"(\d+) passed|(\d+) failed|(\d+) skipped|(\d+) error",
        output,
        re.IGNORECASE,
    )
    for match in re.finditer(r"(\d+) passed", output):
        passed = int(match.group(1))
    for match in re.finditer(r"(\d+) failed", output):
        failed = int(match.group(1))
    for match in re.finditer(r"(\d+) skipped", output):
        skipped = int(match.group(1))
    for match in re.finditer(r"(\d+) error", output):
        errors = int(match.group(1))

    messages = [
        line for line in output.splitlines() if "FAILED" in line or "ERROR" in line
    ][:20]

    if failed > 0 or errors > 0:
        status = CheckStatus.FAIL
    elif "no tests ran" in output.lower():
        status = CheckStatus.SKIP
    else:
        status = CheckStatus.PASS

    return CheckResult(
        name="pytest",
        status=status,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        messages=messages,
    )


def parse_ruff_output(output: str) -> CheckResult:
    error_lines = [line for line in output.splitlines() if line.strip()]
    if not error_lines or "All checks passed" in output:
        return CheckResult(name="ruff", status=CheckStatus.PASS)
    return CheckResult(
        name="ruff",
        status=CheckStatus.FAIL,
        failed=len(error_lines),
        messages=error_lines[:20],
    )
