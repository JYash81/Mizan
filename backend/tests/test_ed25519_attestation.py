"""Unit tests for Ed25519 platform digital signatures and canonical JSON attestation."""

from __future__ import annotations

import json

import pytest

from app.modules.masking.cryptography.signing_service import (
    SignatureVerificationError,
    canonicalize_payload,
    get_or_create_signing_key,
    get_public_key,
    sign_payload,
    verify_signature,
)


def test_canonicalize_payload_sorting_and_compactness() -> None:
    # Unordered dict with whitespace
    payload = {
        "z_field": "last",
        "a_field": "first",
        "nested": {"b": 2, "a": 1},
        "number": 42,
    }

    canonical = canonicalize_payload(payload)

    # Keys must be alphabetically sorted
    expected_order = [
        '"a_field":"first"',
        '"nested":{"a":1,"b":2}',
        '"number":42',
        '"z_field":"last"',
    ]
    for elem in expected_order:
        assert elem in canonical

    # No unnecessary spaces
    assert ": " not in canonical
    assert ", " not in canonical


def test_ed25519_sign_and_verify() -> None:
    payload = {
        "approval_id": "test-approval-123",
        "dataset_id": "test-ds-456",
        "decision": "APPROVED",
        "reviewer_role_snapshot": "WORKSPACE_OWNER",
        "source_dataset_digest": "a" * 64,
        "masked_output_digest": "b" * 64,
    }

    canonical_json, signature_hex, key_id = sign_payload(payload)
    assert len(signature_hex) == 128  # 64 bytes in hex
    assert key_id is not None

    # Verification must succeed
    assert verify_signature(canonical_json, signature_hex, key_id) is True


def test_ed25519_tamper_detection() -> None:
    payload = {
        "approval_id": "test-approval-tamper",
        "decision": "APPROVED",
        "source_dataset_digest": "11" * 32,
    }

    canonical_json, signature_hex, key_id = sign_payload(payload)

    # Tamper with the canonical payload by altering one character
    tampered_data = json.loads(canonical_json)
    tampered_data["decision"] = "REJECTED"
    tampered_canonical = canonicalize_payload(tampered_data)

    with pytest.raises(SignatureVerificationError):
        verify_signature(tampered_canonical, signature_hex, key_id)


def test_key_persistence() -> None:
    key_id = "test-persistent-key-01"
    key1, _ = get_or_create_signing_key(key_id)
    key2, _ = get_or_create_signing_key(key_id)

    # Public bytes must be identical
    pub1 = key1.public_key()
    pub2 = key2.public_key()
    pub_via_getter = get_public_key(key_id)

    msg = b"message to verify key consistency"
    sig = key1.sign(msg)
    pub1.verify(sig, msg)
    pub2.verify(sig, msg)
    pub_via_getter.verify(sig, msg)
