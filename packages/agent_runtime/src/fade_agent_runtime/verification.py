"""Build verification matrices from project profiles."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

from fade_domain.project_profile import ProjectProfile
from fade_verification.verification_matrix import (
    VerificationCheck,
    VerificationLayer,
    VerificationMatrix,
)


def matrix_for_workspace(
    workspace_root: Path,
    profile: ProjectProfile | None,
) -> VerificationMatrix:
    """Derive verification checks from analyzed project commands."""
    env: dict[str, str] | None = None
    src_dir = workspace_root / "src"
    if src_dir.is_dir():
        env = {"PYTHONPATH": str(src_dir.resolve())}

    if profile is None or not profile.commands:
        return VerificationMatrix.minimal()

    checks: list[VerificationCheck] = []
    test_commands = profile.commands.get("test", [])
    lint_commands = profile.commands.get("lint", [])

    for index, command in enumerate(test_commands):
        argv = _normalize_test_argv(shlex.split(command))
        if not argv:
            continue
        checks.append(
            VerificationCheck(
                name=f"test-{index}",
                layer=VerificationLayer.UNIT,
                argv=argv,
                required=True,
                env=env,
            ),
        )

    for index, command in enumerate(lint_commands):
        argv = shlex.split(command)
        if not argv:
            continue
        checks.append(
            VerificationCheck(
                name=f"lint-{index}",
                layer=VerificationLayer.SYNTAX,
                argv=argv,
                required=False,
                env=env,
            ),
        )

    if checks:
        return VerificationMatrix(checks=checks)
    return VerificationMatrix.minimal()


def _normalize_test_argv(argv: list[str]) -> list[str]:
    """Keep pytest scoped to the workspace project root."""
    if not argv or Path(argv[0]).name != "pytest":
        return argv
    if any(arg.startswith("--rootdir") for arg in argv):
        return [sys.executable, "-m", "pytest", *argv[1:]]
    return [sys.executable, "-m", "pytest", "-q", "--rootdir=.", "tests"]
