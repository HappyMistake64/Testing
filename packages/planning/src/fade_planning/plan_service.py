"""Goal planning service."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from fade_domain.goal import Goal
from fade_domain.ids import PlanId
from fade_domain.plan import Plan, PlanStatus, PlanStep
from fade_domain.project_profile import ProjectProfile
from fade_domain.types import RiskLevel
from fade_model_router.router import ModelRouter
from pydantic import ValidationError

from fade_planning.schemas import PlanOutputSchema

_SYSTEM_PROMPT = (
    "You are a software planning assistant. "
    "Respond with JSON only matching this schema:\n"
    "{\n"
    '  "assumptions": ["string"],\n'
    '  "steps": [{\n'
    '    "ordinal": 1,\n'
    '    "title": "...",\n'
    '    "description": "...",\n'
    '    "step_type": "...",\n'
    '    "acceptance_criteria": ["..."]\n'
    "  }],\n"
    '  "test_plan": ["string"],\n'
    '  "risk_level": "low|medium|high|critical"\n'
    "}\n"
)


@dataclass(frozen=True, slots=True)
class ProposePlanCommand:
    goal: Goal
    profile: ProjectProfile | None = None
    model_id: str | None = None


class PlanService:
    """Generate and validate execution plans for goals."""

    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def propose_plan(self, command: ProposePlanCommand, *, version: int = 1) -> Plan:
        context = _build_context(command.goal, command.profile)
        completion = await self._router.complete(
            model_id=command.model_id,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=context,
        )
        parsed = _parse_structured_output(completion.content)
        steps = [
            PlanStep(
                ordinal=s.ordinal,
                title=s.title,
                description=s.description,
                step_type=s.step_type,
                acceptance_criteria=s.acceptance_criteria,
            )
            for s in parsed.steps
        ]
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        return Plan(
            id=PlanId.generate(),
            goal_id=command.goal.id,
            version=version,
            status=PlanStatus.PROPOSED,
            assumptions=parsed.assumptions,
            steps=steps,
            test_plan=parsed.test_plan,
            risk_level=parsed.risk_level,
            created_at=now,
            model_id=completion.model_id,
            raw_output=completion.content,
        )

    @staticmethod
    def validate_output(raw: str) -> PlanOutputSchema:
        """Validate raw model output against plan schema."""
        return _parse_structured_output(raw)


def _build_context(goal: Goal, profile: ProjectProfile | None) -> str:
    lines = [
        f"Goal: {goal.title}",
        f"Intent: {goal.intent}",
        f"Constraints: {', '.join(goal.constraints) or 'none'}",
    ]
    if profile:
        lines.append(f"Languages: {', '.join(profile.languages)}")
        lines.append(f"Frameworks: {', '.join(profile.frameworks)}")
        lines.append(f"Architecture: {profile.architecture_summary}")
    return "\n".join(lines)


def _parse_structured_output(raw: str) -> PlanOutputSchema:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
        return PlanOutputSchema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        fallback = PlanOutputSchema(
            assumptions=["Model output was not valid JSON; using fallback plan"],
            steps=[
                {
                    "ordinal": 1,
                    "title": "Review goal manually",
                    "description": f"Could not parse model output: {exc}",
                    "step_type": "manual",
                    "acceptance_criteria": ["Human review completed"],
                }
            ],
            test_plan=["Manual verification"],
            risk_level=RiskLevel.HIGH,
        )
        return fallback
