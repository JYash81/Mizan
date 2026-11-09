"""Canonical SHA-256 configuration digest calculation for Mizan experiments."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonicalize_config(config: dict[str, Any]) -> str:
    """Produce a deterministic, whitespace-normalized, sorted JSON string for a trial configuration."""

    def _normalize(item: Any) -> Any:
        if isinstance(item, dict):
            return {k: _normalize(item[k]) for k in sorted(item.keys())}
        if isinstance(item, (list, tuple)):
            return [_normalize(x) for x in item]
        if isinstance(item, float):
            return round(item, 6)
        return item

    normalized = _normalize(config)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_canonical_config_digest(config: dict[str, Any]) -> str:
    """Compute the SHA-256 hex digest of a canonical configuration snapshot."""
    canonical_str = canonicalize_config(config)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
