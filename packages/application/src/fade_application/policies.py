"""Guardian policy service."""

from __future__ import annotations

from fade_domain.ids import PolicyId, ProjectId
from fade_domain.policy import PolicyRule
from fade_domain.types import AutonomyLevel
from fade_guardian.policy_resolver import PolicyResolver
from fade_infrastructure.policy_repository import SqlAlchemyPolicyRepository


class PolicyService:
    """Policy CRUD and effective resolution."""

    def __init__(self, repository: SqlAlchemyPolicyRepository) -> None:
        self._repository = repository

    async def list_policies(self) -> list[PolicyRule]:
        rules = await self._repository.list_all()
        if not rules:
            return PolicyResolver.default_global_rules()
        return rules

    async def replace_policies(self, rules: list[PolicyRule]) -> list[PolicyRule]:
        return await self._repository.replace_all(rules)

    async def get_effective_policy(
        self,
        project_id: ProjectId,
        *,
        autonomy_level: AutonomyLevel = AutonomyLevel.ASSISTED,
        workspace_id: str | None = None,
    ):
        rules = await self.list_policies()
        resolver = PolicyResolver(rules)
        return resolver.resolve_effective(
            project_id=project_id,
            autonomy_level=autonomy_level,
            workspace_id=workspace_id,
        )

    async def ensure_defaults(self) -> list[PolicyRule]:
        existing = await self._repository.list_all()
        if existing:
            return existing
        defaults = PolicyResolver.default_global_rules()
        return await self._repository.replace_all(defaults)
