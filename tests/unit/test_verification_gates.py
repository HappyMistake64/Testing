"""Verification gate tests."""

from __future__ import annotations

from pathlib import Path

from fade_tool_gateway.gateway import ToolGateway
from fade_verification.gates import VerificationGate
from fade_verification.result_parsers import parse_pytest_output, parse_ruff_output
from fade_verification.verification_matrix import (
    VerificationCheck,
    VerificationLayer,
    VerificationMatrix,
    VerificationResult,
)


class TestResultParsers:
    def test_parse_pytest_pass(self) -> None:
        result = parse_pytest_output("3 passed in 0.12s")
        assert result.status.value == "pass"
        assert result.passed == 3

    def test_parse_pytest_fail(self) -> None:
        result = parse_pytest_output("1 failed, 2 passed\nFAILED tests/test_x.py")
        assert result.status.value == "fail"
        assert result.failed == 1

    def test_parse_ruff_pass(self) -> None:
        result = parse_ruff_output("All checks passed!")
        assert result.status.value == "pass"

    def test_parse_ruff_fail(self) -> None:
        result = parse_ruff_output("app.py:1:1: E501 line too long")
        assert result.status.value == "fail"


class TestVerificationGate:
    def test_minimal_matrix_passes(self, tmp_path: Path) -> None:
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "main.py").write_text("x = 1\n", encoding="utf-8")
        gateway = ToolGateway.for_workspace(ws)
        gate = VerificationGate(gateway)
        result = gate.run(VerificationMatrix.minimal())
        assert result.result == VerificationResult.PASS

    def test_blocked_command_yields_policy_result(self, tmp_path: Path) -> None:
        ws = tmp_path / "ws"
        ws.mkdir()
        gateway = ToolGateway.for_workspace(ws)
        gate = VerificationGate(gateway)
        matrix = VerificationMatrix(
            checks=[
                VerificationCheck(
                    name="blocked",
                    layer=VerificationLayer.UNIT,
                    argv=["curl", "https://evil.example.com"],
                    required=True,
                ),
            ],
        )
        result = gate.run(matrix)
        assert result.result == VerificationResult.BLOCKED_POLICY
