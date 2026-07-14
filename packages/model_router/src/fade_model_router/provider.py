"""Model provider port and types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelCapability:
    """Provider capability descriptor."""

    provider_id: str
    model_id: str
    available: bool
    supports_structured_output: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ModelCompletion:
    """Result of a model completion request."""

    provider_id: str
    model_id: str
    content: str
    raw: dict[str, Any] | None = None


class ModelProviderPort(ABC):
    """Port for LLM provider adapters."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""

    @abstractmethod
    async def check_availability(self) -> ModelCapability:
        """Return whether this provider is currently usable."""

    @abstractmethod
    async def complete(
        self,
        *,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> ModelCompletion:
        """Run a chat completion."""
