"""OpenAI-compatible cloud adapter."""

from __future__ import annotations

import httpx

from fade_model_router.provider import ModelCapability, ModelCompletion, ModelProviderPort

_DEFAULT_BASE = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIAdapter(ModelProviderPort):
    """OpenAI-compatible chat completions adapter."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE,
        default_model: str = _DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout

    @property
    def provider_id(self) -> str:
        return "openai"

    async def check_availability(self) -> ModelCapability:
        if not self._api_key:
            return ModelCapability(
                provider_id=self.provider_id,
                model_id=self._default_model,
                available=False,
                supports_structured_output=True,
                reason="OpenAI API key not configured",
            )
        return ModelCapability(
            provider_id=self.provider_id,
            model_id=self._default_model,
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
        capability = await self.check_availability()
        if not capability.available:
            msg = capability.reason or "OpenAI unavailable"
            raise RuntimeError(msg)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id or self._default_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""
        return ModelCompletion(
            provider_id=self.provider_id,
            model_id=model_id or self._default_model,
            content=content,
            raw=data,
        )
