"""Mizan Application-Level Cost Policy Enforcement.

Enforces the non-negotiable FREE-ONLY infrastructure policy during development and MVP.
Rejects any paid provider, billable compute, or auto-billing operation by default.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CostPolicyViolationError(Exception):
    """Base exception for cost policy violations."""


class PaidProviderRejectedError(CostPolicyViolationError):
    """Raised when an operation attempts to use a paid provider or billable compute."""


class FreeQuotaExhaustedError(CostPolicyViolationError):
    """Raised when a free API quota is exhausted. Silently falling back to paid is forbidden."""


FREE_PROVIDERS: set[str] = {
    "mock",
    "ollama",
    "gemini_free",
    "fastembed_local",
    "qdrant_local",
}

PAID_PROVIDERS: set[str] = {
    "openai",
    "anthropic",
    "gemini_paid",
    "runpod",
    "lambda_labs",
    "cohere",
    "pinecone",
}


def is_provider_allowed(provider_name: str) -> bool:
    """Check whether a provider is permitted under current cost policy settings."""
    settings = get_settings()
    norm_name = provider_name.strip().lower()

    if norm_name in FREE_PROVIDERS:
        return True

    if norm_name in PAID_PROVIDERS or not norm_name.endswith("_free"):
        return bool(settings.allow_paid_providers)

    return False


def enforce_cost_policy(
    provider_name: str,
    operation_type: str = "inference",
    **kwargs: Any,
) -> None:
    """Validate that the requested provider and operation comply with the free-only mandate.

    Raises:
        PaidProviderRejectedError: if operation requires payment and allow_paid_providers is False.
    """
    settings = get_settings()
    norm_name = provider_name.strip().lower()

    # Paid embedding check
    if operation_type == "embedding" and norm_name not in ("fastembed_local", "mock"):
        if not settings.allow_paid_embedding_apis:
            raise PaidProviderRejectedError(
                f"Embedding provider '{provider_name}' rejected by cost policy: "
                "allow_paid_embedding_apis is False. Use local FastEmbed or Mock."
            )

    # Paid external compute check
    if operation_type == "compute" and norm_name in ("runpod", "lambda_labs"):
        if not settings.allow_billable_external_compute:
            raise PaidProviderRejectedError(
                f"External compute provider '{provider_name}' rejected by cost policy: "
                "allow_billable_external_compute is False."
            )

    # General paid provider check
    if not is_provider_allowed(norm_name):
        raise PaidProviderRejectedError(
            f"Provider '{provider_name}' rejected: "
            "allow_paid_providers is False. Only free local/mock/free-tier providers permitted."
        )


def notify_quota_exhausted(provider_name: str, retry_after_seconds: int | None = None) -> None:
    """Handle free quota exhaustion. Enforces immediate halt without fallback to paid tiers."""
    msg = (
        f"Free quota exhausted for provider '{provider_name}'. "
        "Operation halted per cost policy. Automatic upgrade to paid tier is strictly prohibited."
    )
    if retry_after_seconds:
        msg += f" Retry available after {retry_after_seconds} seconds."
    logger.warning(msg)
    raise FreeQuotaExhaustedError(msg)
