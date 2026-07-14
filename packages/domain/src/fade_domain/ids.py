"""Strongly typed domain identifiers."""

from __future__ import annotations

import re
from typing import Self

from ulid import ULID

_ID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


class _TypedId(str):
    """Base class for ULID-based domain identifiers."""

    __slots__ = ()

    @classmethod
    def generate(cls) -> Self:
        return cls(str(ULID()))

    @classmethod
    def from_string(cls, value: str) -> Self:
        if not _ID_PATTERN.match(value):
            msg = f"Invalid {cls.__name__}: {value!r}"
            raise ValueError(msg)
        return cls(value)

    def __new__(cls, value: str) -> Self:
        if isinstance(value, cls):
            return value
        if not _ID_PATTERN.match(value):
            msg = f"Invalid {cls.__name__}: {value!r}"
            raise ValueError(msg)
        return super().__new__(cls, value)


class ProjectId(_TypedId):
    """Unique identifier for a registered project."""


class JobId(_TypedId):
    """Unique identifier for a durable job."""


class ProfileId(_TypedId):
    """Unique identifier for a project analysis profile."""


class EvidenceId(_TypedId):
    """Unique identifier for an evidence ledger event."""


class GoalId(_TypedId):
    """Unique identifier for a goal."""


class PlanId(_TypedId):
    """Unique identifier for a plan."""


class ArtifactId(_TypedId):
    """Unique identifier for a stored artifact."""


class WorkspaceId(_TypedId):
    """Unique identifier for an isolated workspace."""


class PolicyId(_TypedId):
    """Unique identifier for a policy rule."""
