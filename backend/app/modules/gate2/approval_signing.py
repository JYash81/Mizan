"""Ed25519 Digital Attestation for Gate 2 Financial Approvals."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.modules.masking.cryptography.signing_service import (
    SignatureVerificationError,
    sign_payload,
    verify_signature,
)


def create_and_sign_attestation(
    approval_id: str,
    proposal_id: str,
    proposal_digest: str,
    organization_id: str,
    workspace_id: str,
    approver_id: str,
    approver_role: str,
    max_authorized_budget: str,
    currency: str,
    decision_reason: str,
    key_id: str | None = None,
) -> tuple[str, str, str, datetime]:
    """Create canonical attestation payload and sign with platform Ed25519 key.

    Returns:
        (canonical_signed_payload_json, signature_hex, signing_key_id, signed_at)
    """
    signed_at = datetime.now(UTC)
    signed_at_str = signed_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    payload_dict: dict[str, Any] = {
        "approval_id": approval_id,
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "approver_id": approver_id,
        "approver_role_snapshot": approver_role,
        "decision": "APPROVED",
        "decision_reason": decision_reason,
        "max_authorized_budget": str(max_authorized_budget),
        "currency": currency,
        "signed_at": signed_at_str,
        "schema_version": "gate2-2026-11-09",
    }

    canonical_json, signature_hex, actual_key_id = sign_payload(payload_dict, key_id=key_id)
    return canonical_json, signature_hex, actual_key_id, signed_at


def verify_gate2_attestation(
    signed_payload_json: str,
    signature_hex: str,
    key_id: str,
) -> bool:
    """Verify cryptographic signature on a Gate 2 attestation payload."""
    try:
        return verify_signature(
            canonical_payload=signed_payload_json,
            signature_hex=signature_hex,
            key_id=key_id,
        )
    except SignatureVerificationError:
        return False
    except Exception:
        return False
