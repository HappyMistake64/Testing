"""Policy repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fade_domain.ids import PolicyId
from fade_domain.policy import PolicyEffect, PolicyRule, PolicyRuleType, PolicyScope
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import PolicyModel


class SqlAlchemyPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[PolicyRule]:
        result = await self._session.execute(select(PolicyModel).order_by(PolicyModel.created_at))
        return [_to_domain(row) for row in result.scalars()]

    async def upsert(self, rule: PolicyRule) -> PolicyRule:
        result = await self._session.execute(
            select(PolicyModel).where(PolicyModel.id == str(rule.id)),
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.scope_type = rule.scope_type.value
            existing.scope_id = rule.scope_id
            existing.rule_type = rule.rule_type.value
            existing.effect = rule.effect.value
            existing.parameters_json = json.dumps(rule.parameters)
            existing.version = rule.version
            existing.enabled = rule.enabled
            await self._session.commit()
            await self._session.refresh(existing)
            return _to_domain(existing)

        model = PolicyModel(
            id=str(rule.id),
            scope_type=rule.scope_type.value,
            scope_id=rule.scope_id,
            rule_type=rule.rule_type.value,
            effect=rule.effect.value,
            parameters_json=json.dumps(rule.parameters),
            version=rule.version,
            enabled=rule.enabled,
            created_at=rule.created_at or datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)

    async def replace_all(self, rules: list[PolicyRule]) -> list[PolicyRule]:
        result = await self._session.execute(select(PolicyModel))
        for row in result.scalars():
            await self._session.delete(row)
        saved: list[PolicyRule] = []
        for rule in rules:
            saved.append(await self.upsert(rule))
        return saved


def _to_domain(model: PolicyModel) -> PolicyRule:
    return PolicyRule(
        id=PolicyId(model.id),
        scope_type=PolicyScope(model.scope_type),
        scope_id=model.scope_id,
        rule_type=PolicyRuleType(model.rule_type),
        effect=PolicyEffect(model.effect),
        parameters=json.loads(model.parameters_json) if model.parameters_json else {},
        version=model.version,
        enabled=model.enabled,
        created_at=model.created_at,
    )
