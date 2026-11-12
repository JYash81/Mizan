"""Sealed Evidence Vault: Forensic Escrow with Dual-Authorization and Retention Purging.

Implements Section 7 of Mizan Security Strategy v2:
- Principle: Record what happened by default, not what was in it.
- Prohibited or blocked content is sealed in escrow encrypted under a dedicated AES-GCM evidence key.
- Two-person release requirement: content can only be unsealed with approval of two distinct principals.
- Automated TTL retention enforcement: unsealed or sealed evidence is purged on a strict schedule.
"""

from __future__ import annotations

import base64
import hashlib
import os
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sentinel import (
    SealedEvidenceRecord,
    SealedEvidenceStatus,
)
from app.modules.sentinel.exceptions import (
    EvidenceQuorumRequiredError,
    EvidenceSealedError,
)
from app.modules.sentinel.schemas import (
    SealedEvidenceCreateRequest,
    SealedEvidenceRead,
    UnsealedEvidenceResponse,
)

EVIDENCE_MASTER_KEY_ID = "sentinel_evidence_vault_key"
_STATIC_EVIDENCE_KEY = hashlib.sha256(b"MIZAN_EVIDENCE_VAULT_ENCRYPTION_MASTER_KEY_2026").digest()


def seal_evidence(
    db: Session,
    workspace_id: str,
    payload: SealedEvidenceCreateRequest,
) -> SealedEvidenceRead:
    """Encrypts raw prohibited payload into sealed escrow."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=payload.retention_days)

    raw_bytes = payload.raw_payload.encode("utf-8")
    content_digest = hashlib.sha256(raw_bytes).hexdigest()

    aesgcm = AESGCM(_STATIC_EVIDENCE_KEY)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, raw_bytes, content_digest.encode("utf-8"))

    # Pack nonce + ciphertext
    packed_payload = base64.b64encode(nonce + ciphertext).decode("utf-8")

    record = SealedEvidenceRecord(
        incident_id=payload.incident_id,
        workspace_id=workspace_id,
        encrypted_payload=packed_payload,
        content_digest=content_digest,
        content_type=payload.content_type,
        encryption_key_id=EVIDENCE_MASTER_KEY_ID,
        status=SealedEvidenceStatus.SEALED,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return SealedEvidenceRead.model_validate(record)


def unseal_evidence_dual_approval(
    db: Session,
    evidence_id: str,
    approver_1_id: str,
    approver_2_id: str,
    reason: str,
) -> UnsealedEvidenceResponse:
    """Unseals evidence payload under strict two-person authorization.

    Raises:
        EvidenceQuorumRequiredError: If approvers are identical or missing.
        EvidenceSealedError: If evidence is purged or missing.
    """
    if not approver_1_id or not approver_2_id or approver_1_id == approver_2_id:
        raise EvidenceQuorumRequiredError(
            "Unsealing forensic evidence requires two distinct authorized approvers."
        )

    record = db.execute(
        select(SealedEvidenceRecord).where(SealedEvidenceRecord.id == evidence_id)
    ).scalar_one_or_none()
    if not record:
        raise EvidenceSealedError(f"Sealed evidence record '{evidence_id}' not found.")

    if record.status == SealedEvidenceStatus.PURGED:
        raise EvidenceSealedError(
            "This evidence has already been permanently purged per retention schedule."
        )

    now = datetime.now(UTC)
    record_expires = record.expires_at
    if record_expires.tzinfo is None:
        record_expires = record_expires.replace(tzinfo=UTC)

    if now > record_expires:
        record.status = SealedEvidenceStatus.PURGED
        record.encrypted_payload = "[PURGED_EXPIRED_RETENTION]"
        record.purged_at = now
        db.commit()
        raise EvidenceSealedError("Evidence TTL has expired; record has been purged.")

    # Decrypt AES-GCM
    raw_packed = base64.b64decode(record.encrypted_payload)
    nonce = raw_packed[:12]
    ciphertext = raw_packed[12:]

    aesgcm = AESGCM(_STATIC_EVIDENCE_KEY)
    decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, record.content_digest.encode("utf-8"))
    plaintext = decrypted_bytes.decode("utf-8")

    record.status = SealedEvidenceStatus.RELEASED
    record.release_approver_1_id = approver_1_id
    record.release_approver_2_id = approver_2_id
    record.released_at = now
    db.commit()

    return UnsealedEvidenceResponse(
        evidence_id=record.id,
        incident_id=record.incident_id,
        content_type=record.content_type,
        content_digest=record.content_digest,
        payload=plaintext,
        unsealed_at=now,
        authorized_by=[approver_1_id, approver_2_id],
    )


def purge_expired_evidence_records(db: Session) -> int:
    """Finds and permanently deletes evidence that has reached its retention schedule."""
    now = datetime.now(UTC)
    records = (
        db.execute(
            select(SealedEvidenceRecord).where(
                SealedEvidenceRecord.status != SealedEvidenceStatus.PURGED,
                SealedEvidenceRecord.expires_at <= now,
            )
        )
        .scalars()
        .all()
    )

    count = 0
    for rec in records:
        rec.status = SealedEvidenceStatus.PURGED
        rec.encrypted_payload = "[PURGED_RETENTION_EXPIRED]"
        rec.purged_at = now
        count += 1

    db.commit()
    return count
