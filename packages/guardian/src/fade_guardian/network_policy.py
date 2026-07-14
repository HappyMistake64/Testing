"""Network access policy for commands."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NetworkPolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


NETWORK_COMMANDS = frozenset({
    "curl",
    "wget",
    "npm",
    "pnpm",
    "pip",
    "uv",
    "git",
    "docker",
})


@dataclass(frozen=True, slots=True)
class NetworkPolicyResult:
    decision: NetworkPolicyDecision
    reason: str


class NetworkPolicy:
    """Default-deny network policy with optional per-project allowlist."""

    def __init__(self, allowed_hosts: list[str] | None = None) -> None:
        self._allowed_hosts = set(allowed_hosts or [])

    def evaluate(self, argv: list[str]) -> NetworkPolicyResult:
        if not argv:
            return NetworkPolicyResult(
                decision=NetworkPolicyDecision.DENY,
                reason="Empty command",
            )

        binary = argv[0].split("/")[-1]
        if binary not in NETWORK_COMMANDS:
            return NetworkPolicyResult(
                decision=NetworkPolicyDecision.ALLOW,
                reason="Command does not imply network access",
            )

        if binary == "git" and len(argv) > 1 and argv[1] in {"fetch", "pull", "push", "clone"}:
            return NetworkPolicyResult(
                decision=NetworkPolicyDecision.DENY,
                reason="Git network operations denied by default",
            )

        if (
            binary in {"npm", "pnpm", "pip", "uv"}
            and any(arg in {"install", "add", "sync", "publish"} for arg in argv[1:])
            and not self._allowed_hosts
        ):
            return NetworkPolicyResult(
                decision=NetworkPolicyDecision.DENY,
                reason="Package install network denied without allowlist",
            )

        for arg in argv[1:]:
            if arg.startswith("http://") or arg.startswith("https://"):
                host = self._extract_host(arg)
                if host and host not in self._allowed_hosts:
                    return NetworkPolicyResult(
                        decision=NetworkPolicyDecision.DENY,
                        reason=f"Host not in allowlist: {host}",
                    )

        return NetworkPolicyResult(
            decision=NetworkPolicyDecision.ALLOW,
            reason="Network access permitted",
        )

    def _extract_host(self, url: str) -> str | None:
        without_scheme = url.split("://", 1)[-1]
        host = without_scheme.split("/", 1)[0].split(":", 1)[0]
        return host or None
