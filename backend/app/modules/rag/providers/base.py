"""Base classes and responses for Mizan LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.modules.rag.vector_store.base import ScoredChunk


@dataclass
class LLMResponse:
    """Standardized completion response from any Mizan LLM provider."""

    text: str
    provider_name: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    citations: list[dict[str, Any]] = field(default_factory=list)
    cost_cents: float = 0.0
    finish_reason: str = "stop"


@dataclass
class ProviderStatus:
    """Operational status and free quota availability for a provider."""

    provider_name: str
    is_available: bool
    is_free: bool
    status_message: str
    rate_limit_remaining: int | None = None
    cost_per_million_input_cents: float = 0.0
    cost_per_million_output_cents: float = 0.0


class LLMProvider(ABC):
    """Abstract interface for all Mizan LLM inference providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context_chunks: list[ScoredChunk] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute synchronous completion with citation context."""

    @abstractmethod
    def check_availability(self) -> ProviderStatus:
        """Check whether provider is operational, reachable, and within free quota."""
