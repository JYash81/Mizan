"""Gate 3 Human Release Approval & Ed25519 Cryptographic Attestation Service for Milestone 11."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.artifact_registry import (
    Gate3Approval,
    Gate3Decision,
    Gate3Revocation,
    ModelReleaseEvent,
    ModelVersion,
    ModelVersionStatus,
)
from app.models.identity import User
from app.models.organization import WorkspaceRole
from app.modules.artifact_registry.exceptions import (
    Gate3ApprovalError,
    ImmutableReleaseError,
    ReleaseNotFoundError,
    SeparationOfDutiesViolationError,
    SignaturePurposeMismatchError,
)
from app.modules.masking.cryptography.signing_service import (
    sign_payload,
    verify_signature,
)

GATE3_SIGNATURE_PURPOSE = "GATE3_RELEASE_APPROVAL"
GATE3_SCHEMA_VERSION = "gate3-2026-11-09"


def create_and_sign_gate3_attestation(
    approval_id: str,
    organization_id: str,
    workspace_id: str,
    model_version_id: str,
    family_id: str,
    release_manifest_digest: str,
    decision: Gate3Decision,
    reviewer_user_id: str,
    reviewer_role_snapshot: str,
    decision_reason: str | None = None,
    key_id: str | None = None,
) -> tuple[str, str, str, datetime]:
    """Create deterministic canonical Gate 3 attestation payload and sign with Ed25519 key.

    Returns:
        (canonical_json, signature_hex, signing_key_id, reviewed_at)
    """
    reviewed_at = datetime.now(UTC)
    reviewed_at_str = reviewed_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    payload_dict: dict[str, Any] = {
        "approval_id": approval_id,
        "canonical_version": "1.0",
        "decision": decision.value,
        "decision_reason": decision_reason or "Human release authorization.",
        "family_id": family_id,
        "model_version_id": model_version_id,
        "organization_id": organization_id,
        "release_manifest_digest": release_manifest_digest,
        "reviewed_at": reviewed_at_str,
        "reviewer_role_snapshot": str(reviewer_role_snapshot),
        "reviewer_user_id": reviewer_user_id,
        "schema_version": GATE3_SCHEMA_VERSION,
        "signature_purpose": GATE3_SIGNATURE_PURPOSE,
        "workspace_id": workspace_id,
    }

    canonical_json, signature_hex, actual_key_id = sign_payload(payload_dict, key_id=key_id)
    return canonical_json, signature_hex, actual_key_id, reviewed_at


def verify_gate3_attestation(
    canonical_payload_json: str,
    signature_hex: str,
    key_id: str,
) -> bool:
    """Verify Ed25519 digital signature of Gate 3 attestation.

    Enforces strict signature purpose separation:
    Gate 1 and Gate 2 signatures cannot substitute for Gate 3!
    """
    try:
        payload = json.loads(canonical_payload_json)
    except Exception as e:
        raise Gate3ApprovalError(f"Failed to parse canonical payload JSON: {e}")

    purpose = payload.get("signature_purpose")
    if purpose != GATE3_SIGNATURE_PURPOSE:
        raise SignaturePurposeMismatchError(
            f"Invalid signature purpose '{purpose}'. Expected strictly '{GATE3_SIGNATURE_PURPOSE}'."
        )

    schema_ver = payload.get("schema_version")
    if schema_ver != GATE3_SCHEMA_VERSION:
        raise Gate3ApprovalError(f"Unsupported Gate 3 schema version '{schema_ver}'.")

    return verify_signature(
        canonical_payload=canonical_payload_json,
        signature_hex=signature_hex,
        key_id=key_id,
    )


def submit_gate3_decision(
    db: Session,
    workspace_id: str,
    model_version_id: str,
    reviewer_user: User,
    reviewer_role: WorkspaceRole,
    decision: Gate3Decision,
    decision_reason: str | None = None,
    enforce_separation_of_duties: bool = True,
    signing_key_id: str | None = None,
) -> Gate3Approval:
    """Submit a human Gate 3 release review decision with Ed25519 digital signing.

    Rules & Invariants:
    1. Reviewer role must be WORKSPACE_OWNER or WORKSPACE_ADMIN.
    2. Separation of duties: Creator cannot approve their own release if enforce_separation_of_duties is True.
    3. ModelVersion must be in PENDING_REVIEW status.
    4. ModelVersion must have a valid release_manifest_digest.
    5. Digitally signs canonical attestation payload with purpose GATE3_RELEASE_APPROVAL.
    6. Transition status: APPROVED (immutable) or REJECTED.
    """
    # 1. Check RBAC
    if reviewer_role not in {WorkspaceRole.WORKSPACE_OWNER, WorkspaceRole.WORKSPACE_ADMIN}:
        raise Gate3ApprovalError("Gate 3 release approval requires WORKSPACE_OWNER or WORKSPACE_ADMIN role.", status_code=403)

    # 2. Retrieve Model Version
    version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == model_version_id, ModelVersion.workspace_id == workspace_id)
        .first()
    )
    if not version:
        raise ReleaseNotFoundError(f"Model version '{model_version_id}' not found in workspace.")

    if version.is_immutable:
        raise ImmutableReleaseError(f"Model version '{version.version_tag}' is already finalized or approved.")

    if version.status not in {ModelVersionStatus.PENDING_REVIEW, ModelVersionStatus.REJECTED}:
        raise Gate3ApprovalError(
            f"Cannot review model version in status '{version.status.value}'. Must be PENDING_REVIEW."
        )

    if not version.release_manifest_digest:
        raise Gate3ApprovalError("Cannot approve model version without a finalized Release Manifest.")

    # 3. Separation of Duties Check
    if enforce_separation_of_duties and reviewer_user.id == version.created_by:
        raise SeparationOfDutiesViolationError(
            "Separation of duties violation: The model build creator cannot approve Gate 3 release."
        )

    approval_id = str(uuid.uuid4())

    # 4. Cryptographic Ed25519 Attestation
    canonical_json, signature_hex, actual_key_id, reviewed_at = create_and_sign_gate3_attestation(
        approval_id=approval_id,
        organization_id=version.organization_id,
        workspace_id=workspace_id,
        model_version_id=version.id,
        family_id=version.family_id,
        release_manifest_digest=version.release_manifest_digest,
        decision=decision,
        reviewer_user_id=reviewer_user.id,
        reviewer_role_snapshot=reviewer_role.value if hasattr(reviewer_role, "value") else str(reviewer_role),
        decision_reason=decision_reason,
        key_id=signing_key_id,
    )

    # 5. Persist Gate3Approval
    existing_approval = db.query(Gate3Approval).filter(Gate3Approval.model_version_id == version.id).first()
    if existing_approval:
        db.delete(existing_approval)
        db.flush()

    approval = Gate3Approval(
        id=approval_id,
        organization_id=version.organization_id,
        workspace_id=workspace_id,
        model_version_id=version.id,
        release_manifest_digest=version.release_manifest_digest,
        decision=decision,
        decision_reason=decision_reason,
        reviewer_user_id=reviewer_user.id,
        reviewer_role_snapshot=reviewer_role.value if hasattr(reviewer_role, "value") else str(reviewer_role),
        signature_algorithm="Ed25519",
        signature_purpose=GATE3_SIGNATURE_PURPOSE,
        signing_key_id=actual_key_id,
        approval_signature=signature_hex,
        canonical_payload=canonical_json,
        reviewed_at=reviewed_at,
    )
    db.add(approval)

    # 6. Update ModelVersion Status & Emit Lifecycle Event
    if decision == Gate3Decision.APPROVED:
        version.status = ModelVersionStatus.APPROVED
        event_type = "GATE3_APPROVED"
        msg = f"Model version {version.version_tag} APPROVED by {reviewer_user.email} (Key: {actual_key_id}). Release is now IMMUTABLE."
    else:
        version.status = ModelVersionStatus.REJECTED
        event_type = "GATE3_REJECTED"
        msg = f"Model version {version.version_tag} REJECTED by {reviewer_user.email}. Reason: {decision_reason or 'No reason provided.'}"

    event = ModelReleaseEvent(
        model_version_id=version.id,
        event_type=event_type,
        triggered_by_user_id=reviewer_user.id,
        message=msg,
        metadata_json=json.dumps({
            "decision": decision.value,
            "signature": signature_hex[:16] + "...",
            "signing_key_id": actual_key_id,
        }),
    )
    db.add(event)
    db.commit()
    db.refresh(approval)
    db.refresh(version)
    return approval


def revoke_model_release(
    db: Session,
    workspace_id: str,
    model_version_id: str,
    revoking_user: User,
    revoking_role: WorkspaceRole,
    revocation_reason: str,
) -> Gate3Revocation:
    """Revoke an approved model release with full immutable audit history.

    Rules:
    1. Revoking role must be WORKSPACE_OWNER or WORKSPACE_ADMIN.
    2. Version must currently be in APPROVED status.
    3. An approved Gate3Approval must exist.
    4. Creates immutable Gate3Revocation and sets status to REVOKED.
    """
    if revoking_role not in {WorkspaceRole.WORKSPACE_OWNER, WorkspaceRole.WORKSPACE_ADMIN}:
        raise Gate3ApprovalError("Revoking a release requires WORKSPACE_OWNER or WORKSPACE_ADMIN role.", status_code=403)

    version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == model_version_id, ModelVersion.workspace_id == workspace_id)
        .first()
    )
    if not version:
        raise ReleaseNotFoundError(f"Model version '{model_version_id}' not found in workspace.")

    if version.status != ModelVersionStatus.APPROVED:
        raise Gate3ApprovalError(
            f"Cannot revoke model version in status '{version.status.value}'. Must be APPROVED."
        )

    approval = db.query(Gate3Approval).filter(Gate3Approval.model_version_id == version.id).first()
    if not approval:
        raise Gate3ApprovalError("No Gate3Approval found for this model version.")

    revocation = Gate3Revocation(
        organization_id=version.organization_id,
        workspace_id=workspace_id,
        model_version_id=version.id,
        gate3_approval_id=approval.id,
        revoked_by_user_id=revoking_user.id,
        revoked_by_role_snapshot=revoking_role.value if hasattr(revoking_role, "value") else str(revoking_role),
        revocation_reason=revocation_reason,
        revoked_at=datetime.now(UTC),
    )
    db.add(revocation)

    version.status = ModelVersionStatus.REVOKED

    event = ModelReleaseEvent(
        model_version_id=version.id,
        event_type="REVOKED",
        triggered_by_user_id=revoking_user.id,
        message=f"Model version {version.version_tag} REVOKED by {revoking_user.email}. Reason: {revocation_reason}",
        metadata_json=json.dumps({"revocation_reason": revocation_reason}),
    )
    db.add(event)
    db.commit()
    db.refresh(revocation)
    db.refresh(version)
    return revocation
