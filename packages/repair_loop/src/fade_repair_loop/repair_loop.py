"""Repair iteration with anti-loop hashes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from fade_verification.verification_matrix import VerificationResult

from fade_repair_loop.diagnosis import Diagnosis, FailureClass, Hypothesis


@dataclass(frozen=True, slots=True)
class RepairLoopConfig:
    max_iterations: int = 3
    max_lines_per_iteration: int = 200


@dataclass(frozen=True, slots=True)
class RepairIterationResult:
    iteration: int
    patch_hash: str
    diagnosis: Diagnosis
    verification_result: VerificationResult | None
    blocked: bool = False
    block_reason: str | None = None


class RepairLoop:
    """Manages repair iterations with anti-loop protection."""

    def __init__(self, config: RepairLoopConfig | None = None) -> None:
        self._config = config or RepairLoopConfig()
        self._seen_hashes: set[str] = set()

    def compute_patch_hash(self, patch_content: str) -> str:
        return hashlib.sha256(patch_content.encode("utf-8")).hexdigest()

    def should_block_repeat(self, patch_hash: str) -> bool:
        return patch_hash in self._seen_hashes

    def record_iteration(self, patch_hash: str) -> None:
        self._seen_hashes.add(patch_hash)

    def create_diagnosis(
        self,
        *,
        verification_result: VerificationResult,
        log_excerpt: str,
    ) -> Diagnosis:
        failure_class = FailureClass.UNKNOWN
        if verification_result == VerificationResult.FAIL_CODE:
            failure_class = FailureClass.CODE
        elif verification_result == VerificationResult.FAIL_ENVIRONMENT:
            failure_class = FailureClass.ENVIRONMENT
        elif verification_result == VerificationResult.FAIL_FLAKY:
            failure_class = FailureClass.FLAKY
        elif verification_result == VerificationResult.BLOCKED_POLICY:
            failure_class = FailureClass.POLICY

        return Diagnosis(
            failure_class=failure_class,
            summary=f"Verification returned {verification_result.value}",
            hypotheses=[
                Hypothesis(
                    description="Inspect failing test output and apply minimal fix",
                    confidence=0.6,
                    supporting_evidence=[log_excerpt[:500]] if log_excerpt else [],
                ),
            ],
            relevant_log_excerpt=log_excerpt[:2000],
            suggested_actions=[
                "Review failure classification",
                "Apply minimal targeted patch",
                "Re-run verification matrix",
            ],
            verification_result=verification_result.value,
        )

    def run_iteration(
        self,
        *,
        iteration: int,
        patch_content: str,
        verification_result: VerificationResult | None,
        log_excerpt: str = "",
    ) -> RepairIterationResult:
        if iteration >= self._config.max_iterations:
            return RepairIterationResult(
                iteration=iteration,
                patch_hash="",
                diagnosis=Diagnosis(
                    failure_class=FailureClass.UNKNOWN,
                    summary="Repair budget exhausted",
                    suggested_actions=["Manual intervention required"],
                ),
                verification_result=verification_result,
                blocked=True,
                block_reason="Max repair iterations exceeded",
            )

        patch_hash = self.compute_patch_hash(patch_content)
        if self.should_block_repeat(patch_hash):
            return RepairIterationResult(
                iteration=iteration,
                patch_hash=patch_hash,
                diagnosis=Diagnosis(
                    failure_class=FailureClass.CODE,
                    summary="Repeated patch detected",
                    suggested_actions=["Change approach; do not repeat same patch"],
                ),
                verification_result=verification_result,
                blocked=True,
                block_reason="Anti-loop: duplicate patch hash",
            )

        line_count = patch_content.count("\n") + (1 if patch_content else 0)
        if line_count > self._config.max_lines_per_iteration:
            return RepairIterationResult(
                iteration=iteration,
                patch_hash=patch_hash,
                diagnosis=Diagnosis(
                    failure_class=FailureClass.CODE,
                    summary="Patch exceeds line budget",
                ),
                verification_result=verification_result,
                blocked=True,
                block_reason=f"Patch exceeds {self._config.max_lines_per_iteration} lines",
            )

        self.record_iteration(patch_hash)
        diagnosis = self.create_diagnosis(
            verification_result=verification_result or VerificationResult.INCONCLUSIVE,
            log_excerpt=log_excerpt,
        )
        return RepairIterationResult(
            iteration=iteration,
            patch_hash=patch_hash,
            diagnosis=diagnosis,
            verification_result=verification_result,
        )

    @property
    def seen_hashes(self) -> set[str]:
        return set(self._seen_hashes)
