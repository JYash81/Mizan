"""Unit tests for Mizan Free-Only Cost Policy and Privacy Data-Sharing Guard."""

from __future__ import annotations

import pytest

from app.modules.rag.cost_policy import (
    FreeQuotaExhaustedError,
    PaidProviderRejectedError,
    enforce_cost_policy,
    is_provider_allowed,
    notify_quota_exhausted,
)
from app.modules.rag.privacy_policy import (
    DataClassification,
    PrivacyPolicyViolationError,
    validate_provider_data_sharing,
)


def test_free_providers_allowed_by_default() -> None:
    assert is_provider_allowed("mock") is True
    assert is_provider_allowed("ollama") is True
    assert is_provider_allowed("gemini_free") is True
    assert is_provider_allowed("fastembed_local") is True
    assert is_provider_allowed("qdrant_local") is True

    # None of these should raise
    enforce_cost_policy("mock")
    enforce_cost_policy("ollama")
    enforce_cost_policy("gemini_free")


def test_paid_providers_strictly_rejected() -> None:
    paid_list = ["openai", "anthropic", "gemini_paid", "runpod", "lambda_labs", "cohere", "pinecone"]
    for p in paid_list:
        assert is_provider_allowed(p) is False
        with pytest.raises(PaidProviderRejectedError, match="allow_paid_providers is False"):
            enforce_cost_policy(p)


def test_paid_embedding_and_compute_rejection() -> None:
    with pytest.raises(PaidProviderRejectedError, match="allow_paid_embedding_apis is False"):
        enforce_cost_policy("openai", operation_type="embedding")

    with pytest.raises(PaidProviderRejectedError, match="allow_billable_external_compute is False"):
        enforce_cost_policy("runpod", operation_type="compute")


def test_free_quota_exhaustion_halts_without_paid_upgrade() -> None:
    with pytest.raises(FreeQuotaExhaustedError, match="Automatic upgrade to paid tier is strictly prohibited"):
        notify_quota_exhausted("gemini_free", retry_after_seconds=60)


def test_privacy_policy_sovereign_raw_never_leaves_workstation() -> None:
    # Allowed locally
    validate_provider_data_sharing("mock", classification=DataClassification.SOVEREIGN_RAW)
    validate_provider_data_sharing("ollama", classification=DataClassification.SOVEREIGN_RAW)

    # Strictly forbidden externally
    with pytest.raises(PrivacyPolicyViolationError, match="Raw documents never leave"):
        validate_provider_data_sharing("gemini_free", classification=DataClassification.SOVEREIGN_RAW)


def test_privacy_policy_confidential_customer_requires_opt_in_and_gate1() -> None:
    # Lacks Gate 1 approval
    with pytest.raises(PrivacyPolicyViolationError, match="without prior Gate 1"):
        validate_provider_data_sharing(
            "gemini_free",
            classification=DataClassification.CONFIDENTIAL_CUSTOMER,
            is_gate1_approved=False,
            customer_cloud_opt_in=True,
        )

    # Has Gate 1 approval but lacks customer opt-in
    with pytest.raises(PrivacyPolicyViolationError, match="not provided explicit opt-in"):
        validate_provider_data_sharing(
            "gemini_free",
            classification=DataClassification.CONFIDENTIAL_CUSTOMER,
            is_gate1_approved=True,
            customer_cloud_opt_in=False,
        )

    # Both present -> permitted for external free tier
    validate_provider_data_sharing(
        "gemini_free",
        classification=DataClassification.CONFIDENTIAL_CUSTOMER,
        is_gate1_approved=True,
        customer_cloud_opt_in=True,
    )
