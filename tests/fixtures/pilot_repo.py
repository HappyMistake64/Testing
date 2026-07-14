"""Pilot fixture helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

PILOT_SMALL_SRC = Path(__file__).resolve().parent / "pilot_small"
PILOT_NEUROSTRING_SRC = Path(__file__).resolve().parent / "pilot_neurostring"
PILOT_TRADEPILOT_SRC = Path(__file__).resolve().parent / "pilot_tradepilot"

_FIXTURE_SOURCES: dict[str, Path] = {
    "pilot-small": PILOT_SMALL_SRC,
    "neurostring": PILOT_NEUROSTRING_SRC,
    "tradepilot": PILOT_TRADEPILOT_SRC,
}


def materialize_pilot_repo(target: Path | str) -> Path:
    """Copy pilot_small fixture to target and initialize Git repo."""
    return _materialize_fixture(PILOT_SMALL_SRC, target, "Initial pilot small fixture")


def materialize_named_pilot_repo(target: Path | str, fixture: str) -> Path:
    """Materialize a named pilot fixture into a git repository."""
    source = _FIXTURE_SOURCES.get(fixture)
    if source is None:
        msg = f"Unknown pilot fixture: {fixture}"
        raise ValueError(msg)
    message = {
        "pilot-small": "Initial pilot small fixture",
        "neurostring": "Initial NeuroString pilot fixture",
        "tradepilot": "Initial TradePilot paper fixture",
    }[fixture]
    return _materialize_fixture(source, target, message)


def _materialize_fixture(source: Path, target: Path | str, commit_message: str) -> Path:
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)

    subprocess.run(["git", "init", "-b", "main"], cwd=target, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=target, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", commit_message],
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
