"""Guardian policy tests."""

from __future__ import annotations

from fade_domain.ids import ProjectId
from fade_domain.types import AutonomyLevel
from fade_guardian.policy_resolver import PolicyResolver
from fade_guardian.secret_store import SecretStore


class TestGuardian:
    def test_default_global_rules_deny_rm(self) -> None:
        rules = PolicyResolver.default_global_rules()
        resolver = PolicyResolver(rules)
        effective = resolver.resolve_effective(autonomy_level=AutonomyLevel.AUTONOMOUS)
        effect, _ = resolver.evaluate_command(["rm", "-rf", "/"], effective)
        assert effect.value == "deny"

    def test_read_only_autonomy_limits_commands(self) -> None:
        resolver = PolicyResolver(PolicyResolver.default_global_rules())
        effective = resolver.resolve_effective(autonomy_level=AutonomyLevel.READ_ONLY)
        assert "pytest" not in effective.allowed_commands
        assert "git" in effective.allowed_commands

    def test_secret_store_detects_api_key(self) -> None:
        store = SecretStore()
        key = "sk-" + "a" * 24
        assert store.contains_secret("key=" + key)

    def test_effective_policy_for_project(self) -> None:
        resolver = PolicyResolver(PolicyResolver.default_global_rules())
        project_id = ProjectId.generate()
        effective = resolver.resolve_effective(
            project_id=project_id,
            autonomy_level=AutonomyLevel.ASSISTED,
        )
        assert effective.scope_id == str(project_id)
        assert effective.network_policy == "deny"
