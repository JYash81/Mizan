"""Privacy protection, label cardinality control, and PII/prompt scrubbing for M14 Telemetry."""

from __future__ import annotations

import re
from typing import Any

# Forbidden keys that must never appear in telemetry labels or event payloads
FORBIDDEN_KEY_PATTERNS = {
    "prompt",
    "user_prompt",
    "completion",
    "response_text",
    "message_content",
    "messages",
    "document_text",
    "document_content",
    "file_content",
    "chunk_text",
    "snippet",
    "api_key",
    "secret",
    "password",
    "private_key",
    "token",
    "access_token",
    "authorization",
    "auth_header",
    "user_email",
    "credit_card",
    "ssn",
}

# Regex for common PII patterns
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
BEARER_REGEX = re.compile(r"Bearer\s+[A-Za-z0-9\-_.]+", re.IGNORECASE)
KEY_HEADER_REGEX = re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE)


def validate_and_sanitize_labels(
    metric_key: str,
    labels: dict[str, str],
    allowed_keys: list[str],
) -> dict[str, str]:
    """Validate labels against allowlisted dimensions and strip high-cardinality/unauthorized keys."""
    sanitized: dict[str, str] = {}
    allowed_set = set(allowed_keys)

    for k, v in labels.items():
        k_clean = str(k).strip()
        if k_clean not in allowed_set:
            continue

        # Convert to string and bound length
        v_str = str(v).strip()[:64]

        # Check for forbidden substrings
        if any(f in k_clean.lower() for f in ["prompt", "token", "key", "email", "secret"]):
            continue
        if EMAIL_REGEX.search(v_str):
            v_str = "[REDACTED_EMAIL]"

        sanitized[k_clean] = v_str

    return sanitized


def sanitize_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Recursively scrub any sensitive prompt, model text, document content, or credentials."""
    if not isinstance(payload, dict):
        return {}

    cleaned: dict[str, Any] = {}

    for k, v in payload.items():
        k_str = str(k).lower().strip()

        # Reject explicitly forbidden keys
        if any(forbidden in k_str for forbidden in FORBIDDEN_KEY_PATTERNS):
            cleaned[k] = "[REDACTED_PRIVACY]"
            continue

        # Recursively sanitize dictionaries
        if isinstance(v, dict):
            cleaned[k] = sanitize_event_payload(v)
        elif isinstance(v, list):
            cleaned[k] = [
                sanitize_event_payload(item) if isinstance(item, dict) else _sanitize_scalar_value(item)
                for item in v
            ]
        else:
            cleaned[k] = _sanitize_scalar_value(v)

    return cleaned


def _sanitize_scalar_value(val: Any) -> Any:
    """Sanitize string values for accidental email/bearer tokens/keys."""
    if isinstance(val, str):
        if KEY_HEADER_REGEX.search(val):
            return "[REDACTED_PRIVATE_KEY]"
        if BEARER_REGEX.search(val):
            val = BEARER_REGEX.sub("Bearer [REDACTED]", val)
        if EMAIL_REGEX.search(val):
            val = EMAIL_REGEX.sub("[REDACTED_EMAIL]", val)
        return val[:500]  # Cap scalar text in events to 500 chars
    return val


def assert_no_privacy_violation(data: Any) -> None:
    """Strict verification assertion that data contains no prompt or credential leakage."""
    if isinstance(data, dict):
        for k, v in data.items():
            k_lower = str(k).lower()
            for forbidden in FORBIDDEN_KEY_PATTERNS:
                if forbidden in k_lower and v != "[REDACTED_PRIVACY]":
                    raise ValueError(f"Privacy invariant violation: detected forbidden key '{k}'")
            assert_no_privacy_violation(v)
    elif isinstance(data, list):
        for item in data:
            assert_no_privacy_violation(item)
    elif isinstance(data, str):
        if KEY_HEADER_REGEX.search(data):
            raise ValueError("Privacy invariant violation: raw private key detected")
        if BEARER_REGEX.search(data) and "[REDACTED]" not in data:
            raise ValueError("Privacy invariant violation: live bearer token detected")
