"""Financial Authorization Service and Fail-Closed Policy Enforcement."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.gate2 import Gate2ApprovalStatus
from app.modules.gate2.approval_service import Gate2ApprovalService
from app.modules.gate2.approval_signing import verify_gate2_attestation
from app.modules.gate2.schemas.gate2 import (
    FinancialAuthorizationRequest,
    FinancialAuthorizationResponse,
)


class FinancialAuthorizationService:
    """Evaluates whether an infrastructure execution run is authorized financially and policy-compliant."""

    def __init__(self, approval_service: Gate2ApprovalService | None = None) -> None:
        self.approval_service = approval_service or Gate2ApprovalService()

    def authorize_execution(
        self,
        db: Session,
        req: FinancialAuthorizationRequest,
    ) -> FinancialAuthorizationResponse:
        """Evaluate cryptographic signature, budget limits, and global fail-closed cost policies."""
        settings = get_settings()
        approval = self.approval_service.get_request(db, req.approval_request_id)

        if not approval:
            return FinancialAuthorizationResponse(
                authorized=False,
                status=Gate2ApprovalStatus.REJECTED,
                reason="Gate 2 approval request does not exist.",
                proposal_digest_match=False,
                signature_valid=False,
                policy_allowed=False,
            )

        # Check 1: Expiration
        now = datetime.now(UTC)
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if now > expires_at:
            return FinancialAuthorizationResponse(
                authorized=False,
                status=Gate2ApprovalStatus.EXPIRED,
                reason="Gate 2 approval validity window has expired.",
                proposal_digest_match=False,
                signature_valid=False,
                policy_allowed=False,
                max_authorized_budget=approval.max_authorized_budget,
                estimated_total_cost=approval.estimated_total_cost,
                expires_at=approval.expires_at,
            )

        # Check 2: Revocation
        if approval.status == Gate2ApprovalStatus.REVOKED:
            return FinancialAuthorizationResponse(
                authorized=False,
                status=Gate2ApprovalStatus.REVOKED,
                reason=f"Gate 2 approval was revoked: {approval.revocation_reason or 'No reason specified'}.",
                proposal_digest_match=False,
                signature_valid=False,
                policy_allowed=False,
                max_authorized_budget=approval.max_authorized_budget,
                estimated_total_cost=approval.estimated_total_cost,
                expires_at=approval.expires_at,
            )

        # Check 3: Status must be APPROVED
        if approval.status != Gate2ApprovalStatus.APPROVED:
            return FinancialAuthorizationResponse(
                authorized=False,
                status=approval.status,
                reason=f"Gate 2 approval is not in APPROVED status (current: {approval.status.value}).",
                proposal_digest_match=False,
                signature_valid=False,
                policy_allowed=False,
                max_authorized_budget=approval.max_authorized_budget,
                estimated_total_cost=approval.estimated_total_cost,
                expires_at=approval.expires_at,
            )

        # Check 4: Anti-tamper digest verification
        recomputed_digest = hashlib.sha256(
            approval.proposal_payload_json.encode("utf-8")
        ).hexdigest()
        digest_match = recomputed_digest == approval.proposal_digest
        if not digest_match:
            return FinancialAuthorizationResponse(
                authorized=False,
                status=Gate2ApprovalStatus.INVALIDATED,
                reason="Cryptographic integrity failure: proposal payload does not match proposal digest.",
                proposal_digest_match=False,
                signature_valid=False,
                policy_allowed=False,
                max_authorized_budget=approval.max_authorized_budget,
                estimated_total_cost=approval.estimated_total_cost,
                expires_at=approval.expires_at,
            )

        # Check 5: Digital Signature Verification
        if (
            not approval.signed_payload
            or not approval.approval_signature
            or not approval.signing_key_id
        ):
            return FinancialAuthorizationResponse(
                authorized=False,
                status=Gate2ApprovalStatus.INVALIDATED,
                reason="Missing digital signature attestation records on approved request.",
                proposal_digest_match=True,
                signature_valid=False,
                policy_allowed=False,
                max_authorized_budget=approval.max_authorized_budget,
                estimated_total_cost=approval.estimated_total_cost,
                expires_at=approval.expires_at,
            )

        signature_valid = verify_gate2_attestation(
            signed_payload_json=approval.signed_payload,
            signature_hex=approval.approval_signature,
            key_id=approval.signing_key_id,
        )
        if not signature_valid:
            return FinancialAuthorizationResponse(
                authorized=False,
                status=Gate2ApprovalStatus.INVALIDATED,
                reason="Digital signature verification failed. The attestation has been tampered with or key is invalid.",
                proposal_digest_match=True,
                signature_valid=False,
                policy_allowed=False,
                max_authorized_budget=approval.max_authorized_budget,
                estimated_total_cost=approval.estimated_total_cost,
                expires_at=approval.expires_at,
            )

        # Check 6: Budget Cap
        max_budget = Decimal(approval.max_authorized_budget)
        if req.proposed_cost is not None:
            proposed_dec = Decimal(req.proposed_cost)
            if proposed_dec > max_budget:
                return FinancialAuthorizationResponse(
                    authorized=False,
                    status=Gate2ApprovalStatus.REJECTED,
                    reason=f"Proposed cost ${proposed_dec} exceeds authorized budget cap ${max_budget}.",
                    proposal_digest_match=True,
                    signature_valid=True,
                    policy_allowed=True,
                    max_authorized_budget=str(max_budget),
                    estimated_total_cost=approval.estimated_total_cost,
                    expires_at=approval.expires_at,
                )

        # Check 7: MANDATORY GLOBAL FREE-ONLY INFRASTRUCTURE POLICY ENFORCEMENT
        # If allow_paid_compute is False, any request involving paid compute or cloud provisioning is BLOCKED.
        is_paid_workload = (
            approval.provider_name.lower() != "local"
            or Decimal(approval.estimated_total_cost) > Decimal("0.00")
            or approval.hardware_profile_key != "LOCAL_CPU_I5_8GB"
        )

        if not settings.allow_paid_compute and is_paid_workload:
            return FinancialAuthorizationResponse(
                authorized=False,
                status=Gate2ApprovalStatus.BLOCKED_BY_POLICY,
                reason=(
                    "Execution blocked by policy: Global configuration disallows paid compute "
                    "(allow_paid_compute=False). External cloud or billable hardware cannot be "
                    "provisioned even with valid signed Gate 2 approval."
                ),
                proposal_digest_match=True,
                signature_valid=True,
                policy_allowed=False,
                max_authorized_budget=str(max_budget),
                estimated_total_cost=approval.estimated_total_cost,
                expires_at=approval.expires_at,
                details={
                    "policy": "FREE_RESOURCES_ONLY",
                    "allow_paid_compute": settings.allow_paid_compute,
                    "provider": approval.provider_name,
                    "estimated_cost": approval.estimated_total_cost,
                },
            )

        # All checks passed!
        return FinancialAuthorizationResponse(
            authorized=True,
            status=Gate2ApprovalStatus.APPROVED,
            reason="Execution authorized: Gate 2 approval is valid, digitally signed, and policy compliant.",
            proposal_digest_match=True,
            signature_valid=True,
            policy_allowed=True,
            max_authorized_budget=str(max_budget),
            estimated_total_cost=approval.estimated_total_cost,
            expires_at=approval.expires_at,
            details={
                "provider": approval.provider_name,
                "instance_type": approval.instance_type,
                "signing_key_id": approval.signing_key_id,
            },
        )
