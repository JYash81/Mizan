"""Central AI LLM Provider Factory and Capability Registry."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.modules.rag.cost_policy import enforce_cost_policy
from app.modules.rag.providers.base import LLMProvider, ProviderStatus
from app.modules.rag.providers.gemini_free_provider import GeminiFreeProvider
from app.modules.rag.providers.mock_provider import MockLLMProvider
from app.modules.rag.providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def get_llm_provider(provider_name: str | None = None, **kwargs: Any) -> LLMProvider:
    """Retrieve an initialized LLMProvider instance under cost policy enforcement."""
    settings = get_settings()
    name = (provider_name or settings.default_llm_provider).strip().lower()

    enforce_cost_policy(name, operation_type="inference")

    if name == "mock":
        return MockLLMProvider(**kwargs)

    if name == "ollama":
        return OllamaProvider(**kwargs)

    if name == "gemini_free":
        return GeminiFreeProvider(**kwargs)

    raise ValueError(f"Unknown or unsupported provider: '{provider_name}'")


def list_registered_providers() -> list[ProviderStatus]:
    """Inspect and report the live status of all registered free providers."""
    providers = [
        MockLLMProvider(),
        OllamaProvider(),
        GeminiFreeProvider(),
    ]
    return [p.check_availability() for p in providers]
