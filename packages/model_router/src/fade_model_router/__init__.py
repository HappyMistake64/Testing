"""Model router package."""

from fade_model_router.ollama_adapter import OllamaAdapter
from fade_model_router.openai_adapter import OpenAIAdapter
from fade_model_router.provider import ModelCapability, ModelCompletion, ModelProviderPort
from fade_model_router.router import ModelRouter, create_default_router

__all__ = [
    "ModelCapability",
    "ModelCompletion",
    "ModelProviderPort",
    "ModelRouter",
    "OllamaAdapter",
    "OpenAIAdapter",
    "create_default_router",
]
