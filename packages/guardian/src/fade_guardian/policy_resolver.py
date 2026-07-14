"""Autonomy and policy resolution."""

from __future__ import annotations

from fade_domain.ids import PolicyId, ProjectId
from fade_domain.policy import (
    EffectivePolicy,
    PolicyEffect,
    PolicyRule,
    PolicyRuleType,
    PolicyScope,
)
from fade_domain.types import AutonomyLevel


DEFAULT_PROTECTED_PATHS = [
    ".env",
    ".ssh",
    "credentials",
    "secrets",
]

DEFAULT_ALLOWED_COMMANDS = [
    "git",
    "pytest",
    "uv",
    "ruff",
    "python",
    "npm",
    "node",
]

AUTONOMY_COMMAND_MATRIX: dict[AutonomyLevel, set[str]] = {
    AutonomyLevel.READ_ONLY: {"git"},
    AutonomyLevel.PLAN: {"git"},
    AutonomyLevel.ASSISTED: {"git", "pytest", "ruff", "python", "uv"},
    AutonomyLevel.SUPERVISED: {"git", "pytest", "ruff", "python", "uv", "npm", "node"},
    AutonomyLevel.AUTONOMOUS: {"git", "pytest", "ruff", "python", "uv", "npm", "node"},
}


class PolicyResolver:
    """Resolves effective policy from layered rules."""

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self._rules = rules or []

    def resolve_effective(
        self,
        *,
        project_id: ProjectId | None = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.READ_ONLY,
        workspace_id: str | None = None,
    ) -> EffectivePolicy:
        applicable = self._filter_rules(project_id, workspace_id)
        denied_commands = self._denied_commands(applicable)
        allowed = [
            cmd
            for cmd in AUTONOMY_COMMAND_MATRIX.get(autonomy_level, set())
            if cmd not in denied_commands
        ]
        if not allowed:
            allowed = list(AUTONOMY_COMMAND_MATRIX.get(AutonomyLevel.READ_ONLY, set()))

        protected_paths = list(DEFAULT_PROTECTED_PATHS)
        for rule in applicable:
            if rule.rule_type == PolicyRuleType.PATH and rule.effect == PolicyEffect.DENY:
                paths = rule.parameters.get("paths", [])
                if isinstance(paths, list):
                    protected_paths.extend(str(p) for p in paths)

        network_policy = "deny"
        for rule in applicable:
            if rule.rule_type == PolicyRuleType.NETWORK:
                if rule.effect == PolicyEffect.ALLOW:
                    network_policy = "allow"
                elif rule.effect == PolicyEffect.DENY:
                    network_policy = "deny"

        return EffectivePolicy(
            scope_type=PolicyScope.PROJECT if project_id else PolicyScope.GLOBAL,
            scope_id=str(project_id) if project_id else None,
            rules=applicable,
            autonomy_level=autonomy_level.value,
            allowed_commands=sorted(set(allowed)),
            network_policy=network_policy,
            protected_paths=sorted(set(protected_paths)),
        )

    def evaluate_command(
        self,
        argv: list[str],
        effective: EffectivePolicy,
    ) -> tuple[PolicyEffect, str]:
        if not argv:
            return PolicyEffect.DENY, "Empty command"

        binary = argv[0].split("/")[-1]
        if binary not in effective.allowed_commands:
            return PolicyEffect.DENY, f"Command {binary} not allowed at autonomy {effective.autonomy_level}"

        for rule in effective.rules:
            if rule.rule_type != PolicyRuleType.COMMAND:
                continue
            pattern = str(rule.parameters.get("binary", ""))
            if pattern and pattern == binary:
                if rule.effect == PolicyEffect.DENY:
                    return PolicyEffect.DENY, f"Denied by rule {rule.id}"
                if rule.effect == PolicyEffect.REQUIRE_APPROVAL:
                    return PolicyEffect.REQUIRE_APPROVAL, f"Approval required by rule {rule.id}"

        return PolicyEffect.ALLOW, "Allowed by effective policy"

    def _filter_rules(
        self,
        project_id: ProjectId | None,
        workspace_id: str | None,
    ) -> list[PolicyRule]:
        result: list[PolicyRule] = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.scope_type == PolicyScope.GLOBAL:
                result.append(rule)
            elif rule.scope_type == PolicyScope.PROJECT and project_id and rule.scope_id == str(
                project_id
            ):
                result.append(rule)
            elif rule.scope_type == PolicyScope.WORKSPACE and workspace_id and rule.scope_id == workspace_id:
                result.append(rule)
        return result

    def _denied_commands(self, rules: list[PolicyRule]) -> set[str]:
        denied: set[str] = set()
        for rule in rules:
            if rule.rule_type == PolicyRuleType.COMMAND and rule.effect == PolicyEffect.DENY:
                binary = rule.parameters.get("binary")
                if isinstance(binary, str):
                    denied.add(binary)
        return denied

    @staticmethod
    def default_global_rules() -> list[PolicyRule]:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        return [
            PolicyRule(
                id=PolicyId.generate(),
                scope_type=PolicyScope.GLOBAL,
                scope_id=None,
                rule_type=PolicyRuleType.COMMAND,
                effect=PolicyEffect.DENY,
                parameters={"binary": "rm"},
                version=1,
                enabled=True,
                created_at=now,
            ),
            PolicyRule(
                id=PolicyId.generate(),
                scope_type=PolicyScope.GLOBAL,
                scope_id=None,
                rule_type=PolicyRuleType.COMMAND,
                effect=PolicyEffect.DENY,
                parameters={"binary": "curl"},
                version=1,
                enabled=True,
                created_at=now,
            ),
            PolicyRule(
                id=PolicyId.generate(),
                scope_type=PolicyScope.GLOBAL,
                scope_id=None,
                rule_type=PolicyRuleType.NETWORK,
                effect=PolicyEffect.DENY,
                parameters={},
                version=1,
                enabled=True,
                created_at=now,
            ),
        ]
