"""Subprocess runner - the only module allowed to invoke subprocess."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result of a subprocess invocation."""

    argv: list[str]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


def run_command(
    argv: list[str],
    *,
    cwd: str,
    timeout_s: int = 120,
    max_output_bytes: int = 5_000_000,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a command without shell=True."""
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            check=False,
        )
        stdout = proc.stdout[:max_output_bytes]
        stderr = proc.stderr[:max_output_bytes]
        return CommandResult(
            argv=argv,
            cwd=cwd,
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace")[:max_output_bytes]
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")[:max_output_bytes]
        return CommandResult(
            argv=argv,
            cwd=cwd,
            exit_code=-1,
            stdout=stdout,
            stderr=stderr or "command timed out",
            timed_out=True,
        )
