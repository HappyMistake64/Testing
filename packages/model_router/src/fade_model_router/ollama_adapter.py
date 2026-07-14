"""Ollama local model adapter with graceful fallback."""

from __future__ import annotations

import httpx

from fade_model_router.provider import ModelCapability, ModelCompletion, ModelProviderPort

_DEFAULT_BASE = "http://127.0.0.1:11434"
_DEFAULT_MODEL = "llama3.2"


class OllamaAdapter(ModelProviderPort):
    """Ollama HTTP API adapter."""

    def __init__(
        self,
        *,
        base_url: str = _DEFAULT_BASE,
        default_model: str = _DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout

    @property
    def provider_id(self) -> str:
        return "ollama"

    async def check_availability(self) -> ModelCapability:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                if response.status_code == 200:
                    return ModelCapability(
                        provider_id=self.provider_id,
                        model_id=self._default_model,
                        available=True,
                        supports_structured_output=False,
                    )
        except (httpx.HTTPError, OSError):
            pass
        return ModelCapability(
            provider_id=self.provider_id,
            model_id=self._default_model,
            available=False,
            supports_structured_output=False,
            reason="Ollama is not reachable",
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
            msg = capability.reason or "Ollama unavailable"
            raise RuntimeError(msg)

        payload = {
            "model": model_id or self._default_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        content = data.get("message", {}).get("content", "")
        return ModelCompletion(
            provider_id=self.provider_id,
            model_id=model_id or self._default_model,
            content=content,
            raw=data,
        )
