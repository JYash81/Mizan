"""Deterministic Masking Engine for Mizan.

Applies masking strategies to text using validated PII findings and human review decisions.
Produces immutable masked output text and calculates SHA-256 integrity digests.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.models.masking import DecisionType, FindingStatus, MaskingStrategy
from app.modules.masking.services.offset_service import (
    sort_spans_descending,
    spans_overlap,
    validate_offsets,
)

# Entity precedence for resolving overlapping detections to the most specific label
ENTITY_PRECEDENCE: dict[str, int] = {
    "UAE_EMIRATES_ID": 100,
    "UAE_IBAN": 100,
    "UAE_PHONE_NUMBER": 100,
    "CREDIT_CARD": 90,
    "IBAN_CODE": 80,
    "EMAIL_ADDRESS": 80,
    "PHONE_NUMBER": 70,
    "PERSON": 60,
    "LOCATION": 50,
    "DATE_TIME": 40,
}


def compute_sha256(text: str) -> str:
    """Compute SHA-256 hex digest over UTF-8 encoded text string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def format_partial_mask(entity_type: str, original_text: str) -> str:
    """Generate safe partial mask revealing non-sensitive structural portions."""
    clean = original_text.strip()
    if entity_type == "UAE_EMIRATES_ID":
        if "-" in clean and len(clean) == 18:
            # Format: 784-1985-1234567-1 -> 784-1985-XXXXXXX-1
            return f"{clean[:8]}-XXXXXXX-{clean[-1]}"
        elif len(clean) == 15 and clean.isdigit():
            return f"{clean[:7]}XXXXXXX{clean[-1]}"
        return "[PARTIAL_UAE_EMIRATES_ID]"

    if entity_type == "UAE_IBAN":
        no_spaces = clean.replace(" ", "")
        if len(no_spaces) >= 8:
            return f"{no_spaces[:4]}...{no_spaces[-4:]}"
        return "[PARTIAL_UAE_IBAN]"

    if entity_type in ("UAE_PHONE_NUMBER", "PHONE_NUMBER"):
        if len(clean) >= 6:
            return f"{clean[:4]}***{clean[-2:]}"
        return "[PARTIAL_PHONE]"

    if entity_type == "EMAIL_ADDRESS":
        if "@" in clean:
            local, domain = clean.split("@", 1)
            visible_local = local[:2] if len(local) >= 2 else local[:1]
            return f"{visible_local}***@{domain}"
        return "[PARTIAL_EMAIL]"

    if len(clean) <= 4:
        return "****"
    return f"{clean[:2]}***{clean[-2:]}"


def determine_replacement(
    entity_type: str,
    original_text: str,
    strategy: MaskingStrategy,
    custom_replacement: str | None = None,
) -> str:
    """Determine the replacement string for a detected sensitive span."""
    if custom_replacement:
        return custom_replacement

    if strategy == MaskingStrategy.REDACT:
        return "[REDACTED]"

    if strategy == MaskingStrategy.PARTIAL_MASK:
        return format_partial_mask(entity_type, original_text)

    # Default: REPLACE_WITH_ENTITY_LABEL
    return f"[{entity_type}]"


def mask_text(
    canonical_text: str,
    findings: list[dict[str, Any]],
    decisions_by_finding_id: dict[str, Any] | None = None,
    strategy: MaskingStrategy = MaskingStrategy.REPLACE_WITH_ENTITY_LABEL,
) -> tuple[str, int, str]:
    """Mask sensitive spans in canonical_text deterministically.

    Returns:
        (masked_text, applied_masks_count, sha256_digest)
    """
    if not canonical_text:
        digest = compute_sha256("")
        return "", 0, digest

    text_len = len(canonical_text)
    decisions = decisions_by_finding_id or {}

    # Filter findings: skip FALSE_POSITIVE
    active_spans: list[dict[str, Any]] = []
    for f in findings:
        fid = f.get("id")
        decision = decisions.get(fid)

        # Check decision override
        if decision:
            d_type = (
                decision.decision_type.value
                if hasattr(decision.decision_type, "value")
                else str(decision.decision_type)
            )
            if d_type == DecisionType.FALSE_POSITIVE.value:
                continue
            custom_repl = getattr(decision, "custom_replacement", None)
        else:
            status = (
                f.get("status").value
                if hasattr(f.get("status"), "value")
                else str(f.get("status", FindingStatus.DETECTED.value))
            )
            if status == FindingStatus.FALSE_POSITIVE.value:
                continue
            custom_repl = None

        start = f["start_offset"]
        end = f["end_offset"]
        validate_offsets(start, end, text_len)

        original_span = canonical_text[start:end]
        replacement = determine_replacement(f["entity_type"], original_span, strategy, custom_repl)

        active_spans.append(
            {
                "start_offset": start,
                "end_offset": end,
                "entity_type": f["entity_type"],
                "replacement": replacement,
                "score": f.get("detection_score", 0.5),
                "precedence": ENTITY_PRECEDENCE.get(f["entity_type"], 10),
            }
        )

    if not active_spans:
        digest = compute_sha256(canonical_text)
        return canonical_text, 0, digest

    # Resolve overlapping spans into non-overlapping replacement tasks
    # Sort spans ascending by start
    active_spans.sort(key=lambda s: (s["start_offset"], s["end_offset"]))

    clusters: list[list[dict[str, Any]]] = []
    for span in active_spans:
        if not clusters:
            clusters.append([span])
        else:
            # Check if span overlaps with the current cluster
            cluster_end = max(s["end_offset"] for s in clusters[-1])
            cluster_start = min(s["start_offset"] for s in clusters[-1])
            if (
                spans_overlap(cluster_start, cluster_end, span["start_offset"], span["end_offset"])
                or span["start_offset"] < cluster_end
            ):
                clusters[-1].append(span)
            else:
                clusters.append([span])

    # For each cluster, pick the winning replacement and interval
    consolidated_replacements: list[dict[str, Any]] = []
    for cluster in clusters:
        # Interval spans the full extent of the cluster
        c_start = min(s["start_offset"] for s in cluster)
        c_end = max(s["end_offset"] for s in cluster)

        # Pick highest precedence, then highest score
        winner = max(cluster, key=lambda s: (s["precedence"], s["score"]))

        consolidated_replacements.append(
            {
                "start_offset": c_start,
                "end_offset": c_end,
                "replacement": winner["replacement"],
            }
        )

    # Sort descending by start_offset to apply replacements without offset drift
    sorted_replacements = sort_spans_descending(consolidated_replacements)

    result_chars = list(canonical_text)
    for rep in sorted_replacements:
        start = rep["start_offset"]
        end = rep["end_offset"]
        result_chars[start:end] = list(rep["replacement"])

    masked_text = "".join(result_chars)
    applied_count = len(sorted_replacements)
    digest = compute_sha256(masked_text)

    return masked_text, applied_count, digest
