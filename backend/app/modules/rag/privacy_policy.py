"""Mizan Data Privacy & External Provider Data-Sharing Guard.

Enforces that:
1. Raw unmasked business documents NEVER leave the sovereign Workshop Data Plane.
2. External cloud providers (such as Gemini free tier) NEVER receive confidential customer data.
3. Gate 1 approval alone does NOT authorize external cloud sharing without explicit opt-in.
"""

from __future__ import annotations

import enum
import logging

logger = logging.getLogger(__name__)


class DataClassification(str, enum.Enum):
    PUBLIC = "PUBLIC"
    SYNTHETIC = "SYNTHETIC"
    INTERNAL_NON_CONFIDENTIAL = "INTERNAL_NON_CONFIDENTIAL"
    CONFIDENTIAL_CUSTOMER = "CONFIDENTIAL_CUSTOMER"
    SOVEREIGN_RAW = "SOVEREIGN_RAW"


class PrivacyPolicyViolationError(Exception):
    """Raised when data sharing violates privacy boundaries."""


# External cloud providers that transmit data outside the local machine
EXTERNAL_CLOUD_PROVIDERS: set[str] = {
    "gemini_free",
    "gemini_paid",
    "openai",
    "anthropic",
}

# Sovereign/local providers that never transmit data off the workstation
SOVEREIGN_LOCAL_PROVIDERS: set[str] = {
    "mock",
    "ollama",
    "fastembed_local",
    "qdrant_local",
}


def validate_provider_data_sharing(
    provider_name: str,
    classification: DataClassification,
    is_gate1_approved: bool = False,
    customer_cloud_opt_in: bool = False,
) -> None:
    """Validate whether the data classification and governance status permit usage with the provider.

    Rules:
    - SOVEREIGN_RAW: Strictly prohibited from ALL external cloud providers.
    - CONFIDENTIAL_CUSTOMER: Prohibited from external cloud providers even if masked,
      unless customer has explicitly opted in AND Gate 1 approval is active.
    - Local and Mock providers are permitted for all classifications within the local boundary.
    """
    norm_provider = provider_name.strip().lower()

    # Local and Mock providers never leave the workstation
    if norm_provider in SOVEREIGN_LOCAL_PROVIDERS:
        return

    # External cloud provider checks
    if norm_provider in EXTERNAL_CLOUD_PROVIDERS:
        if classification == DataClassification.SOVEREIGN_RAW:
            raise PrivacyPolicyViolationError(
                f"Sovereign raw data cannot be sent to external provider '{provider_name}'. "
                "Raw documents never leave the Workshop Data Plane."
            )

        if classification == DataClassification.CONFIDENTIAL_CUSTOMER:
            if not is_gate1_approved:
                raise PrivacyPolicyViolationError(
                    f"Confidential data cannot be sent to external provider '{provider_name}' "
                    "without prior Gate 1 human approval."
                )
            if not customer_cloud_opt_in:
                raise PrivacyPolicyViolationError(
                    f"External cloud provider '{provider_name}' rejected: "
                    "Customer has not provided explicit opt-in for external cloud AI processing."
                )

        logger.info(
            "Privacy check passed for external provider '%s' (Classification: %s, Gate 1: %s)",
            provider_name,
            classification.value,
            is_gate1_approved,
        )
