"""Offline model adapter returning structured JSON plans and implementations."""

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

_STUB_IMPLEMENTATION = {
    "changes": [
        {
            "path": "src/pilot_app/main.py",
            "new_content": (
                '"""Main entry point for pilot small fixture."""\n\n\n'
                "def greet(name: str) -> str:\n"
                '    return f"Hello, {name}! Welcome to FADE."\n\n\n'
                "def add(a: int, b: int) -> int:\n"
                "    return a + b\n"
            ),
            "reason": "Extend greet() with FADE welcome text",
        },
        {
            "path": "tests/test_main.py",
            "new_content": (
                "from pilot_app.main import add, greet\n\n\n"
                "def test_greet() -> None:\n"
                '    assert greet("FADE") == "Hello, FADE! Welcome to FADE."\n\n\n'
                "def test_add() -> None:\n"
                "    assert add(2, 3) == 5\n"
            ),
            "reason": "Update test expectation for greet() change",
        },
    ],
    "summary": "Extend greet() with FADE welcome message",
}


class StubModelAdapter(ModelProviderPort):
    """Offline model adapter returning structured JSON for planning and implementation."""

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
        prompt = system_prompt.lower()
        if "personal assistant" in prompt:
            return ModelCompletion(
                provider_id=self.provider_id,
                model_id="stub-assistant",
                content=(
                    "Offline stub answer. Configure Ollama or a cloud provider "
                    "for real conversational answers."
                ),
                raw={"stub": True, "user_prompt": user_prompt[:200]},
            )
        if "implementation agent" in prompt or "repair agent" in prompt:
            payload = _STUB_IMPLEMENTATION
            model_name = "stub-implementer"
        else:
            payload = _STUB_PLAN
            model_name = model_id or "stub-planner"

        return ModelCompletion(
            provider_id=self.provider_id,
            model_id=model_name,
            content=json.dumps(payload),
            raw={"stub": True, "user_prompt": user_prompt[:200]},
        )
