"""Model router with provider selection and fallback."""

from __future__ import annotations

from fade_model_router.ollama_adapter import OllamaAdapter
from fade_model_router.openai_adapter import OpenAIAdapter
from fade_model_router.provider import ModelCapability, ModelCompletion, ModelProviderPort
from fade_model_router.stub_adapter import StubModelAdapter


class ModelRouter:
    """Select first available provider for completions."""

    def __init__(self, providers: list[ModelProviderPort] | None = None) -> None:
        self._providers: list[ModelProviderPort] = providers or []

    def register(self, provider: ModelProviderPort) -> None:
        self._providers.append(provider)

    async def list_capabilities(self) -> list[ModelCapability]:
        return [await p.check_availability() for p in self._providers]

    async def complete(
        self,
        *,
        model_id: str | None = None,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> ModelCompletion:
        last_error: Exception | None = None
        for provider in self._providers:
            capability = await provider.check_availability()
            if not capability.available:
                continue
            try:
                return await provider.complete(
                    model_id=model_id or capability.model_id,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
        if last_error:
            raise last_error
        msg = "No model providers available"
        raise RuntimeError(msg)


def create_default_router(
    *,
    openai_api_key: str | None = None,
    ollama_base_url: str = "http://127.0.0.1:11434",
    ollama_default_model: str = "llama3.2",
    include_stub: bool = False,
) -> ModelRouter:
    """Create router with Ollama first, OpenAI as fallback, optional stub for tests."""
    router = ModelRouter()
    router.register(OllamaAdapter(base_url=ollama_base_url, default_model=ollama_default_model))
    router.register(OpenAIAdapter(api_key=openai_api_key))
    if include_stub:
        router.register(StubModelAdapter())
    return router
