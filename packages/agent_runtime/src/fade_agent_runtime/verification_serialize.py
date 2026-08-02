"""Serialize verification gate results for job checkpoints."""

from __future__ import annotations

from fade_verification.gates import VerificationGateResult


def serialize_verification(gate_result: VerificationGateResult) -> dict[str, object]:
    return {
        "result": gate_result.result.value,
        "summary": gate_result.summary,
        "checks": [
            {
                "name": execution.check.name,
                "layer": execution.check.layer.value,
                "required": execution.check.required,
                "exit_code": execution.exit_code,
                "blocked": execution.blocked,
                "block_reason": execution.block_reason,
                "stdout_tail": execution.stdout[-500:] if execution.stdout else "",
                "stderr_tail": execution.stderr[-500:] if execution.stderr else "",
            }
            for execution in gate_result.executions
        ],
    }
