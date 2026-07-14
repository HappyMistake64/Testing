"""Guardian policy domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from fade_domain.ids import PolicyId


class PolicyScope(StrEnum):
    """Scope at which a policy rule applies."""

    GLOBAL = "global"
    PROJECT = "project"
    WORKSPACE = "workspace"
    JOB = "job"


class PolicyEffect(StrEnum):
    """Effect of a policy rule."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyRuleType(StrEnum):
    """Categories of policy rules."""

    COMMAND = "command"
    PATH = "path"
    NETWORK = "network"
    AUTONOMY = "autonomy"
    SECRET = "secret"
    PROTECTED_ACTION = "protected_action"


@dataclass(slots=True)
class PolicyRule:
    """A single policy rule."""

    id: PolicyId
    scope_type: PolicyScope
    scope_id: str | None
    rule_type: PolicyRuleType
    effect: PolicyEffect
    parameters: dict[str, object]
    version: int
    enabled: bool
    created_at: datetime | None = None


@dataclass(slots=True)
class EffectivePolicy:
    """Resolved effective policy for a context."""

    scope_type: PolicyScope
    scope_id: str | None
    rules: list[PolicyRule]
    autonomy_level: str
    allowed_commands: list[str]
    network_policy: str
    protected_paths: list[str]
