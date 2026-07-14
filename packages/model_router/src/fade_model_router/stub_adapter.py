"""Deterministic stub provider for tests and offline pilots."""

from __future__ import annotations

import json

from fade_model_router.provider import ModelCapability, ModelCompletion, ModelProviderPort

_STUB_PLAN = {
    "assumptions": ["Pilot environment uses deterministic stub planner"],
    "steps": [
        {
            "ordinal": 1,
            "title": "Analyze scope",
            "description": "Review goal and project profile",
            "step_type": "analysis",
            "acceptance_criteria": ["Scope documented"],
        },
        {
            "ordinal": 2,
            "title": "Implement minimal change",
            "description": "Apply focused patch in isolated workspace",
            "step_type": "implementation",
            "acceptance_criteria": ["Diff ready for review"],
        },
        {
            "ordinal": 3,
            "title": "Verify",
            "description": "Run project test command",
            "step_type": "verification",
            "acceptance_criteria": ["Tests pass"],
        },
    ],
    "test_plan": ["Run detected test command"],
    "risk_level": "low",
}


class StubModelAdapter(ModelProviderPort):
    """Offline model adapter returning structured JSON plans."""

    @property
    def provider_id(self) -> str:
        return "stub"

    async def check_availability(self) -> ModelCapability:
        return ModelCapability(
            provider_id=self.provider_id,
            model_id="stub-planner",
            available=True,
            supports_structured_output=True,
        )

    async def complete(
        self,
        *,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> ModelCompletion:
        return ModelCompletion(
            provider_id=self.provider_id,
            model_id=model_id or "stub-planner",
            content=json.dumps(_STUB_PLAN),
            raw={"stub": True, "user_prompt": user_prompt[:200]},
        )
