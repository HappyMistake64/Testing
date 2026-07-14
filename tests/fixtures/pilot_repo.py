"""Pilot fixture helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

PILOT_SMALL_SRC = Path(__file__).resolve().parent / "pilot_small"


def materialize_pilot_repo(target: Path | str) -> Path:
    """Copy pilot_small fixture to target and initialize Git repo."""
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(PILOT_SMALL_SRC, target)

    subprocess.run(["git", "init", "-b", "main"], cwd=target, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=target, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial pilot small fixture"],
        cwd=target,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "FADE",
            "GIT_AUTHOR_EMAIL": "fade@test.local",
            "GIT_COMMITTER_NAME": "FADE",
            "GIT_COMMITTER_EMAIL": "fade@test.local",
        },
    )
    return target
