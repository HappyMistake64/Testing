"""Guardian policy API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from apps.api.dependencies import get_policy_service
from fade_application.policies import PolicyService
from fade_domain.ids import PolicyId, ProjectId
from fade_domain.policy import PolicyEffect, PolicyRule, PolicyRuleType, PolicyScope
from fade_domain.types import AutonomyLevel
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(tags=["policies"])


class PolicyRuleResponse(BaseModel):
    id: str
    scope_type: str
    scope_id: str | None
    rule_type: str
    effect: str
    parameters: dict[str, Any]
    version: int
    enabled: bool
    created_at: datetime | None = None


class PolicyListResponse(BaseModel):
    items: list[PolicyRuleResponse]
    total: int


class PolicyRuleRequest(BaseModel):
    id: str | None = None
    scope_type: str
    scope_id: str | None = None
    rule_type: str
    effect: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    enabled: bool = True


class ReplacePoliciesRequest(BaseModel):
    rules: list[PolicyRuleRequest]


class EffectivePolicyResponse(BaseModel):
    scope_type: str
    scope_id: str | None
    autonomy_level: str
    allowed_commands: list[str]
    network_policy: str
    protected_paths: list[str]
    rule_count: int


def _to_response(rule: PolicyRule) -> PolicyRuleResponse:
    return PolicyRuleResponse(
        id=str(rule.id),
        scope_type=rule.scope_type.value,
        scope_id=rule.scope_id,
        rule_type=rule.rule_type.value,
        effect=rule.effect.value,
        parameters=rule.parameters,
        version=rule.version,
        enabled=rule.enabled,
        created_at=rule.created_at,
    )


@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    service: Annotated[PolicyService, Depends(get_policy_service)],
) -> PolicyListResponse:
    rules = await service.list_policies()
    items = [_to_response(r) for r in rules]
    return PolicyListResponse(items=items, total=len(items))


@router.put("/policies", response_model=PolicyListResponse)
async def replace_policies(
    body: ReplacePoliciesRequest,
    service: Annotated[PolicyService, Depends(get_policy_service)],
) -> PolicyListResponse:
    rules: list[PolicyRule] = []
    for item in body.rules:
        try:
            rules.append(
                PolicyRule(
                    id=PolicyId.from_string(item.id) if item.id else PolicyId.generate(),
                    scope_type=PolicyScope(item.scope_type),
                    scope_id=item.scope_id,
                    rule_type=PolicyRuleType(item.rule_type),
                    effect=PolicyEffect(item.effect),
                    parameters=item.parameters,
                    version=item.version,
                    enabled=item.enabled,
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    saved = await service.replace_policies(rules)
    items = [_to_response(r) for r in saved]
    return PolicyListResponse(items=items, total=len(items))


@router.get("/projects/{project_id}/policies/effective", response_model=EffectivePolicyResponse)
async def get_effective_policy(
    project_id: str,
    service: Annotated[PolicyService, Depends(get_policy_service)],
    autonomy_level: str = Query(default="assisted"),
    workspace_id: str | None = Query(default=None),
) -> EffectivePolicyResponse:
    try:
        autonomy = AutonomyLevel.from_string(autonomy_level)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    effective = await service.get_effective_policy(
        ProjectId.from_string(project_id),
        autonomy_level=autonomy,
        workspace_id=workspace_id,
    )
    return EffectivePolicyResponse(
        scope_type=effective.scope_type.value,
        scope_id=effective.scope_id,
        autonomy_level=effective.autonomy_level,
        allowed_commands=effective.allowed_commands,
        network_policy=effective.network_policy,
        protected_paths=effective.protected_paths,
        rule_count=len(effective.rules),
    )
