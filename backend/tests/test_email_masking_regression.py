"""Regression coverage for email-like text on reserved test domains."""

from __future__ import annotations

import pytest

from app.models.masking import MaskingStrategy
from app.modules.masking.services.detection_service import detect_pii_in_text
from app.modules.masking.services.masking_service import mask_text


@pytest.mark.parametrize("address", ["qa.e2e@example.invalid", "qa.e2e@example.test"])
def test_reserved_domain_email_is_detected_and_masked_as_a_full_span(address: str) -> None:
    text = f"Synthetic email placeholder: {address}"

    findings = detect_pii_in_text(text)
    email_findings = [
        finding
        for finding in findings
        if finding["entity_type"] == "EMAIL_ADDRESS"
        and text[finding["start_offset"] : finding["end_offset"]] == address
    ]

    assert email_findings, "The full reserved-domain email should be recognized as EMAIL_ADDRESS"

    masked, applied_masks, _ = mask_text(
        canonical_text=text,
        findings=findings,
        strategy=MaskingStrategy.REPLACE_WITH_ENTITY_LABEL,
    )

    assert applied_masks == 1
    assert masked == "Synthetic email placeholder: [EMAIL_ADDRESS]"
    assert address not in masked
    assert "qa.e2e@[URL]valid" not in masked
