"""Tool Gateway policy checks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from fade_guardian.network_policy import NetworkPolicy, NetworkPolicyDecision
from fade_guardian.secret_store import SecretStore


class PolicyDecision(StrEnum):
    """Authorization decision for a tool call."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True, slots=True)
class PolicyCheckResult:
    """Outcome of a policy evaluation."""

    decision: PolicyDecision
    rule_ids: list[str]
    reason: str


PROTECTED_PATH_SEGMENTS = frozenset({
    ".env",
    ".ssh",
    "id_rsa",
    "credentials",
    "secrets",
})

DEFAULT_COMMAND_ALLOWLIST: dict[str, frozenset[str]] = {
    "git": frozenset({"status", "diff", "log", "show", "rev-parse", "branch"}),
    "pytest": frozenset(),
    "uv": frozenset({"run", "sync"}),
    "ruff": frozenset({"check", "format"}),
    "python": frozenset({"-m", "-c"}),
    "npm": frozenset({"test", "run", "ci"}),
    "node": frozenset(),
}


class ToolPolicy:
    """Evaluates tool calls against path, command and network policies."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        secret_store: SecretStore | None = None,
        network_policy: NetworkPolicy | None = None,
        command_allowlist: dict[str, frozenset[str]] | None = None,
        lease_token: str | None = None,
        expected_lease_token: str | None = None,
        write_allowed: bool = False,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._secret_store = secret_store or SecretStore()
        self._network_policy = network_policy or NetworkPolicy()
        self._command_allowlist = command_allowlist or DEFAULT_COMMAND_ALLOWLIST
        self._lease_token = lease_token
        self._expected_lease_token = expected_lease_token
        self._write_allowed = write_allowed

    def check_read_path(self, relative_path: str) -> PolicyCheckResult:
        resolved = self._resolve_in_workspace(relative_path)
        if resolved is None:
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                rule_ids=["PATH-WORKSPACE-ONLY"],
                reason=f"Path escapes workspace: {relative_path}",
            )
        if self._is_protected(resolved):
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                rule_ids=["PATH-PROTECTED"],
                reason=f"Protected path denied: {relative_path}",
            )
        return PolicyCheckResult(
            decision=PolicyDecision.ALLOW,
            rule_ids=["PATH-WORKSPACE-ONLY"],
            reason="Read within workspace",
        )

    def check_write_path(self, relative_path: str) -> PolicyCheckResult:
        if not self._write_allowed:
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                rule_ids=["WRITE-NO-LEASE"],
                reason="Write not allowed without lease",
            )
        if self._expected_lease_token and self._lease_token != self._expected_lease_token:
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                rule_ids=["LEASE-FENCING"],
                reason="Invalid or missing lease token",
            )
        return self.check_read_path(relative_path)

    def check_command(self, argv: list[str], *, network_required: bool = False) -> PolicyCheckResult:
        if not argv:
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                rule_ids=["CMD-EMPTY"],
                reason="Empty command",
            )

        binary = Path(argv[0]).name
        if binary not in self._command_allowlist:
            return PolicyCheckResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                rule_ids=["CMD-UNKNOWN"],
                reason=f"Command not in allowlist: {binary}",
            )

        allowed_subcommands = self._command_allowlist[binary]
        if allowed_subcommands and len(argv) > 1 and argv[1] not in allowed_subcommands:
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                rule_ids=["CMD-SUBCOMMAND"],
                reason=f"Subcommand not allowed for {binary}: {argv[1]}",
            )

        if network_required:
            net = self._network_policy.evaluate(argv)
            if net.decision != NetworkPolicyDecision.ALLOW:
                return PolicyCheckResult(
                    decision=PolicyDecision.DENY,
                    rule_ids=["NET-DENY"],
                    reason=net.reason,
                )

        return PolicyCheckResult(
            decision=PolicyDecision.ALLOW,
            rule_ids=[f"CMD-ALLOW-{binary.upper()}"],
            reason="Command allowed by policy",
        )

    def redact_output(self, text: str) -> str:
        return self._secret_store.redact(text)

    def _resolve_in_workspace(self, relative_path: str) -> Path | None:
        if not relative_path or relative_path.startswith("/"):
            candidate = Path(relative_path)
        else:
            candidate = self._workspace_root / relative_path

        try:
            resolved = candidate.resolve()
        except OSError:
            return None

        try:
            resolved.relative_to(self._workspace_root)
        except ValueError:
            return None

        if os.path.islink(candidate) and not os.path.islink(resolved):
            try:
                link_target = os.readlink(candidate)
                if link_target.startswith("/"):
                    target = Path(link_target).resolve()
                    target.relative_to(self._workspace_root)
            except (OSError, ValueError):
                return None

        return resolved

    def _is_protected(self, path: Path) -> bool:
        parts = {part.lower() for part in path.parts}
        return bool(parts & PROTECTED_PATH_SEGMENTS)
