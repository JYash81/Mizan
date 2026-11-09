"""Deterministic Canonical Digest Computation for Gate 2 Financial Proposals."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonicalize_dict(payload: dict[str, Any]) -> str:
    """Serialize dictionary into deterministic canonical JSON string.

    Rules:
    - Sorted keys alphabetically
    - Compact separators (no spaces: ',', ':')
    - UTF-8 characters preserved
    - None represented as null
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_proposal_digest(proposal_data: dict[str, Any]) -> tuple[str, str]:
    """Compute deterministic SHA-256 digest and canonical JSON string for proposal data.

    Returns:
        (canonical_json_string, sha256_hex_digest)
    """
    canonical_json = canonicalize_dict(proposal_data)
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return canonical_json, digest


def verify_proposal_digest(proposal_data: dict[str, Any], expected_digest: str) -> bool:
    """Verify that proposal data matches the expected SHA-256 digest."""
    _, actual_digest = compute_proposal_digest(proposal_data)
    return actual_digest == expected_digest
