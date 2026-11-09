"""Gate 1 Human Approval Service and Invariant Enforcement.

Enforces that NO dataset enters the external experimentation pipeline without
explicit, cryptographically signed approval from an authorized human reviewer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import DatasetVersion, DatasetVersionStatus
from app.models.identity import User
from app.models.masking import (
    ExtractionCoverage,
    Gate1Approval,
    Gate1ApprovalEvent,
    Gate1Decision,
    MaskingRun,
    MaskingRunStatus,
    PiiFinding,
)
from app.models.organization import Workspace
from app.modules.masking.cryptography.signing_service import (
    sign_payload,
    verify_signature,
)
from app.modules.storage.provider import StorageProvider

logger = logging.getLogger(__name__)


class Gate1ApprovalError(Exception):
    """Raised when Gate 1 approval validation or execution fails."""


def compute_findings_digest(findings: list[PiiFinding]) -> str:
    """Calculate deterministic SHA-256 digest over sorted findings."""
    sorted_findings = sorted(
        findings,
        key=lambda f: (f.document_id, f.start_offset, f.end_offset, f.entity_type),
    )
    records = []
    for f in sorted_findings:
        records.append(
            {
                "id": f.id,
                "document_id": f.document_id,
                "entity_type": f.entity_type,
                "start_offset": f.start_offset,
                "end_offset": f.end_offset,
                "status": f.status.value if hasattr(f.status, "value") else str(f.status),
                "score": round(float(f.detection_score), 4),
            }
        )
    canonical_repr = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def approve_gate1(
    db: Session,
    workspace_id: str,
    masking_run_id: str,
    reviewer_user: User,
    reviewer_role_snapshot: str,
    decision_reason: str | None = None,
    storage: StorageProvider | None = None,
    override_coverage_reason: str | None = None,
) -> Gate1Approval:
    """Execute and cryptographically sign a Gate 1 Human Approval."""
    run = db.execute(
        select(MaskingRun).where(
            MaskingRun.id == masking_run_id,
            MaskingRun.workspace_id == workspace_id,
        )
    ).scalar_one_or_none()
    if not run:
        raise Gate1ApprovalError(f"MaskingRun {masking_run_id} not found in workspace.")

    if run.status != MaskingRunStatus.COMPLETED:
        raise Gate1ApprovalError(
            f"Cannot approve Gate 1: MaskingRun status is '{run.status.value}', expected 'COMPLETED'."
        )

    # Validate OCR & Extraction Coverage guard
    if run.extraction_coverage in (
        ExtractionCoverage.OCR_REQUIRED,
        ExtractionCoverage.EXTRACTION_FAILED,
    ):
        if not override_coverage_reason:
            raise Gate1ApprovalError(
                f"Cannot approve Gate 1: Extraction coverage is '{run.extraction_coverage.value}'. "
                "All documents requiring OCR or with failed extraction must be resolved or explicitly excluded with justification."
            )

    # Validate dataset version
    version = db.execute(
        select(DatasetVersion).where(DatasetVersion.id == run.dataset_version_id)
    ).scalar_one_or_none()
    if not version:
        raise Gate1ApprovalError(f"DatasetVersion {run.dataset_version_id} not found.")

    if version.status != DatasetVersionStatus.READY:
        raise Gate1ApprovalError(
            f"Cannot approve Gate 1: DatasetVersion is in status '{version.status.value}', expected 'READY'."
        )

    # Workspace & Organization
    workspace = db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    ).scalar_one_or_none()
    if not workspace:
        raise Gate1ApprovalError(f"Workspace {workspace_id} not found.")

    # Load findings to compute digest
    findings = (
        db.execute(select(PiiFinding).where(PiiFinding.masking_run_id == run.id)).scalars().all()
    )
    findings_digest = compute_findings_digest(list(findings))

    approval_id = str(uuid.uuid4())
    reviewed_at = datetime.now(UTC)
    reviewed_at_str = reviewed_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Canonical payload for digital attestation
    canonical_payload_dict = {
        "approval_id": approval_id,
        "canonical_version": "1.0",
        "dataset_id": run.dataset_id,
        "decision": Gate1Decision.APPROVED.value,
        "decision_reason": decision_reason or "Approved by authorized human reviewer.",
        "findings_digest": findings_digest,
        "masked_output_digest": run.masked_output_digest or "",
        "masking_run_id": run.id,
        "organization_id": workspace.organization_id,
        "reviewed_at": reviewed_at_str,
        "reviewer_role_snapshot": str(reviewer_role_snapshot),
        "reviewer_user_id": reviewer_user.id,
        "schema_version": "2026-11-08",
        "source_dataset_digest": run.source_dataset_digest,
        "source_dataset_version_id": run.dataset_version_id,
        "workspace_id": workspace_id,
    }

    canonical_json, signature_hex, signing_key_id = sign_payload(canonical_payload_dict)

    approval = Gate1Approval(
        id=approval_id,
        organization_id=workspace.organization_id,
        workspace_id=workspace_id,
        dataset_id=run.dataset_id,
        dataset_version_id=run.dataset_version_id,
        masking_run_id=run.id,
        source_dataset_digest=run.source_dataset_digest,
        masked_output_digest=run.masked_output_digest or "",
        findings_digest=findings_digest,
        reviewer_user_id=reviewer_user.id,
        reviewer_role_snapshot=str(reviewer_role_snapshot),
        decision=Gate1Decision.APPROVED,
        decision_reason=decision_reason,
        signature_algorithm="Ed25519",
        signing_key_id=signing_key_id,
        approval_signature=signature_hex,
        canonical_payload=canonical_json,
        reviewed_at=reviewed_at,
    )
    db.add(approval)

    # Audit event
    event = Gate1ApprovalEvent(
        approval_id=approval.id,
        event_type="GATE1_APPROVED",
        actor_user_id=reviewer_user.id,
        details_json=json.dumps(
            {
                "masking_run_id": run.id,
                "dataset_version_id": run.dataset_version_id,
                "findings_count": len(findings),
                "reviewer_role": str(reviewer_role_snapshot),
                "signing_key_id": signing_key_id,
            }
        ),
    )
    db.add(event)

    db.commit()
    db.refresh(approval)
    return approval


def reject_gate1(
    db: Session,
    workspace_id: str,
    masking_run_id: str,
    reviewer_user: User,
    reviewer_role_snapshot: str,
    decision_reason: str,
) -> Gate1Approval:
    """Execute a Gate 1 Rejection decision."""
    run = db.execute(
        select(MaskingRun).where(
            MaskingRun.id == masking_run_id,
            MaskingRun.workspace_id == workspace_id,
        )
    ).scalar_one_or_none()
    if not run:
        raise Gate1ApprovalError(f"MaskingRun {masking_run_id} not found in workspace.")

    workspace = db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    ).scalar_one_or_none()
    if not workspace:
        raise Gate1ApprovalError(f"Workspace {workspace_id} not found.")

    findings = (
        db.execute(select(PiiFinding).where(PiiFinding.masking_run_id == run.id)).scalars().all()
    )
    findings_digest = compute_findings_digest(list(findings))

    approval_id = str(uuid.uuid4())
    reviewed_at = datetime.now(UTC)
    reviewed_at_str = reviewed_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    canonical_payload_dict = {
        "approval_id": approval_id,
        "canonical_version": "1.0",
        "dataset_id": run.dataset_id,
        "decision": Gate1Decision.REJECTED.value,
        "decision_reason": decision_reason,
        "findings_digest": findings_digest,
        "masked_output_digest": run.masked_output_digest or "",
        "masking_run_id": run.id,
        "organization_id": workspace.organization_id,
        "reviewed_at": reviewed_at_str,
        "reviewer_role_snapshot": str(reviewer_role_snapshot),
        "reviewer_user_id": reviewer_user.id,
        "schema_version": "2026-11-08",
        "source_dataset_digest": run.source_dataset_digest,
        "source_dataset_version_id": run.dataset_version_id,
        "workspace_id": workspace_id,
    }

    canonical_json, signature_hex, signing_key_id = sign_payload(canonical_payload_dict)

    approval = Gate1Approval(
        id=approval_id,
        organization_id=workspace.organization_id,
        workspace_id=workspace_id,
        dataset_id=run.dataset_id,
        dataset_version_id=run.dataset_version_id,
        masking_run_id=run.id,
        source_dataset_digest=run.source_dataset_digest,
        masked_output_digest=run.masked_output_digest or "",
        findings_digest=findings_digest,
        reviewer_user_id=reviewer_user.id,
        reviewer_role_snapshot=str(reviewer_role_snapshot),
        decision=Gate1Decision.REJECTED,
        decision_reason=decision_reason,
        signature_algorithm="Ed25519",
        signing_key_id=signing_key_id,
        approval_signature=signature_hex,
        canonical_payload=canonical_json,
        reviewed_at=reviewed_at,
    )
    db.add(approval)

    event = Gate1ApprovalEvent(
        approval_id=approval.id,
        event_type="GATE1_REJECTED",
        actor_user_id=reviewer_user.id,
        details_json=json.dumps({"reason": decision_reason}),
    )
    db.add(event)

    db.commit()
    db.refresh(approval)
    return approval


def verify_gate1_approval(
    db: Session,
    approval_id: str,
    storage: StorageProvider | None = None,
) -> bool:
    """Verify cryptographic integrity and active status of a Gate 1 Approval."""
    approval = db.execute(
        select(Gate1Approval).where(Gate1Approval.id == approval_id)
    ).scalar_one_or_none()
    if not approval:
        return False

    if approval.decision != Gate1Decision.APPROVED:
        return False

    # Verify Ed25519 digital signature
    try:
        verify_signature(
            canonical_payload=approval.canonical_payload,
            signature_hex=approval.approval_signature,
            key_id=approval.signing_key_id,
        )
    except Exception:
        return False

    # Verify source dataset version still exists and matches source digest
    version = db.execute(
        select(DatasetVersion).where(DatasetVersion.id == approval.dataset_version_id)
    ).scalar_one_or_none()
    if not version or version.content_hash != approval.source_dataset_digest:
        return False

    return True


def require_gate1_approval(
    db: Session,
    workspace_id: str,
    dataset_version_id: str,
    storage: StorageProvider | None = None,
) -> Gate1Approval:
    """Central reusable guard for downstream milestones (Milestone 5 RAG and Milestone 7 Experiments).

    Raises HTTP 403 Forbidden if Gate 1 approval is missing, invalid, or tampered.
    """
    approval = (
        db.execute(
            select(Gate1Approval)
            .where(
                Gate1Approval.workspace_id == workspace_id,
                Gate1Approval.dataset_version_id == dataset_version_id,
                Gate1Approval.decision == Gate1Decision.APPROVED,
            )
            .order_by(Gate1Approval.created_at.desc())
        )
        .scalars()
        .first()
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "GATE1_APPROVAL_REQUIRED",
                "message": (
                    "Access denied: This dataset version has not received mandatory "
                    "Gate 1 Human Approval for personal data protection."
                ),
            },
        )

    if not verify_gate1_approval(db, approval.id, storage):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "GATE1_APPROVAL_INVALID",
                "message": (
                    "Access denied: Gate 1 approval attestation is invalid, modified, or revoked."
                ),
            },
        )

    return approval
