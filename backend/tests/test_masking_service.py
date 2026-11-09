"""Unit tests for deterministic Masking Engine and masking strategies."""

from __future__ import annotations

import hashlib

from app.models.masking import FindingStatus, MaskingStrategy
from app.modules.masking.services.masking_service import compute_sha256, mask_text


def test_mask_text_replace_with_entity_label() -> None:
    text = "Contact Alice at alice@example.com or call 0501234567."
    findings = [
        {
            "id": "f1",
            "start_offset": 8,
            "end_offset": 13,
            "entity_type": "PERSON",
            "detection_score": 0.85,
            "status": FindingStatus.DETECTED,
        },
        {
            "id": "f2",
            "start_offset": 17,
            "end_offset": 34,
            "entity_type": "EMAIL_ADDRESS",
            "detection_score": 0.95,
            "status": FindingStatus.DETECTED,
        },
        {
            "id": "f3",
            "start_offset": 43,
            "end_offset": 53,
            "entity_type": "UAE_PHONE_NUMBER",
            "detection_score": 0.9,
            "status": FindingStatus.DETECTED,
        },
    ]

    masked, count, digest = mask_text(
        canonical_text=text,
        findings=findings,
        strategy=MaskingStrategy.REPLACE_WITH_ENTITY_LABEL,
    )

    assert count == 3
    assert masked == "Contact [PERSON] at [EMAIL_ADDRESS] or call [UAE_PHONE_NUMBER]."
    assert digest == hashlib.sha256(masked.encode("utf-8")).hexdigest()


def test_mask_text_redact_strategy() -> None:
    text = "Resident ID: 784-1985-1234567-1."
    findings = [
        {
            "id": "f1",
            "start_offset": 13,
            "end_offset": 31,
            "entity_type": "UAE_EMIRATES_ID",
            "detection_score": 0.95,
            "status": FindingStatus.DETECTED,
        }
    ]

    masked, count, _ = mask_text(
        canonical_text=text,
        findings=findings,
        strategy=MaskingStrategy.REDACT,
    )

    assert count == 1
    assert masked == "Resident ID: [REDACTED]."


def test_mask_text_partial_mask_strategy() -> None:
    text = "Emirates ID: 784-1985-1234567-1, IBAN: AE140330000000000000000, Email: user@mizan.ae"
    findings = [
        {
            "id": "f1",
            "start_offset": 13,
            "end_offset": 31,
            "entity_type": "UAE_EMIRATES_ID",
            "detection_score": 0.95,
            "status": FindingStatus.DETECTED,
        },
        {
            "id": "f2",
            "start_offset": 39,
            "end_offset": 62,
            "entity_type": "UAE_IBAN",
            "detection_score": 0.95,
            "status": FindingStatus.DETECTED,
        },
        {
            "id": "f3",
            "start_offset": 71,
            "end_offset": 84,
            "entity_type": "EMAIL_ADDRESS",
            "detection_score": 0.9,
            "status": FindingStatus.DETECTED,
        },
    ]

    masked, count, _ = mask_text(
        canonical_text=text,
        findings=findings,
        strategy=MaskingStrategy.PARTIAL_MASK,
    )

    assert count == 3
    assert "784-1985-XXXXXXX-1" in masked
    assert "AE14...0000" in masked
    assert "us***@mizan.ae" in masked


def test_mask_text_false_positive_skipping() -> None:
    text = "Invoice number: 123456789."
    findings = [
        {
            "id": "f1",
            "start_offset": 16,
            "end_offset": 25,
            "entity_type": "PHONE_NUMBER",
            "detection_score": 0.5,
            "status": FindingStatus.FALSE_POSITIVE,
        }
    ]

    masked, count, digest = mask_text(
        canonical_text=text,
        findings=findings,
        strategy=MaskingStrategy.REPLACE_WITH_ENTITY_LABEL,
    )

    # Skipped due to false positive
    assert count == 0
    assert masked == text
    assert digest == compute_sha256(text)


def test_mask_text_overlapping_detections_resolution() -> None:
    # Text where an Emirates ID was also matched as a general US_DRIVER_LICENSE or number
    text = "ID: 784-1985-1234567-1"
    findings = [
        {
            "id": "f1",
            "start_offset": 4,
            "end_offset": 22,
            "entity_type": "UAE_EMIRATES_ID",
            "detection_score": 0.95,
            "status": FindingStatus.DETECTED,
        },
        {
            "id": "f2",
            "start_offset": 13,
            "end_offset": 20,
            "entity_type": "US_DRIVER_LICENSE",
            "detection_score": 0.1,
            "status": FindingStatus.DETECTED,
        },
    ]

    masked, count, _ = mask_text(
        canonical_text=text,
        findings=findings,
        strategy=MaskingStrategy.REPLACE_WITH_ENTITY_LABEL,
    )

    # Overlapping span should resolve to single replacement with higher precedence
    assert count == 1
    assert masked == "ID: [UAE_EMIRATES_ID]"


def test_empty_text_masking() -> None:
    masked, count, digest = mask_text("", [])
    assert masked == ""
    assert count == 0
    assert digest == hashlib.sha256(b"").hexdigest()
