"""Platform Ed25519 Cryptographic Attestation and Canonical Payload Service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.config import get_settings


class CryptographicError(Exception):
    """Base cryptographic operation error."""


class SignatureVerificationError(CryptographicError):
    """Raised when digital signature verification fails."""


def canonicalize_payload(payload: dict[str, Any]) -> str:
    """Serialize dictionary into deterministic canonical JSON string.

    Invariants:
    - Keys sorted alphabetically
    - Compact separators (',', ':')
    - No whitespace
    - UTF-8 characters preserved (ensure_ascii=False)
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _get_key_paths(key_id: str) -> tuple[Path, Path]:
    settings = get_settings()
    keys_dir = Path(settings.signing_keys_dir)
    keys_dir.mkdir(parents=True, exist_ok=True)
    priv_path = keys_dir / f"{key_id}.key"
    pub_path = keys_dir / f"{key_id}.pub"
    return priv_path, pub_path


def get_or_create_signing_key(
    key_id: str | None = None,
) -> tuple[ed25519.Ed25519PrivateKey, str]:
    """Retrieve an existing Ed25519 platform key or generate one if absent."""
    settings = get_settings()
    actual_key_id = key_id or settings.default_signing_key_id
    priv_path, pub_path = _get_key_paths(actual_key_id)

    if priv_path.exists():
        with open(priv_path, "rb") as f:
            priv_bytes = f.read()
        private_key = serialization.load_pem_private_key(priv_bytes, password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise CryptographicError(f"Key {actual_key_id} is not an Ed25519 private key.")
        return private_key, actual_key_id

    # Generate new key
    private_key = ed25519.Ed25519PrivateKey.generate()
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(priv_path, "wb") as f:
        f.write(priv_pem)
    with open(pub_path, "wb") as f:
        f.write(pub_pem)

    return private_key, actual_key_id


def get_public_key(key_id: str) -> ed25519.Ed25519PublicKey:
    """Retrieve public key for a key ID."""
    _, pub_path = _get_key_paths(key_id)
    if not pub_path.exists():
        # Fallback to loading/generating key
        priv_key, _ = get_or_create_signing_key(key_id)
        return priv_key.public_key()

    with open(pub_path, "rb") as f:
        pub_bytes = f.read()
    public_key = serialization.load_pem_public_key(pub_bytes)
    if not isinstance(public_key, ed25519.Ed25519PublicKey):
        raise CryptographicError(f"Key {key_id} is not an Ed25519 public key.")
    return public_key


def sign_payload(
    payload: dict[str, Any],
    key_id: str | None = None,
) -> tuple[str, str, str]:
    """Canonicalize payload and generate Ed25519 signature.

    Returns:
        (canonical_json_string, signature_hex, key_id)
    """
    private_key, actual_key_id = get_or_create_signing_key(key_id)
    canonical_json = canonicalize_payload(payload)
    sig_bytes = private_key.sign(canonical_json.encode("utf-8"))
    signature_hex = sig_bytes.hex()
    return canonical_json, signature_hex, actual_key_id


def verify_signature(
    canonical_payload: str,
    signature_hex: str,
    key_id: str,
) -> bool:
    """Verify an Ed25519 signature against a canonical JSON payload string."""
    public_key = get_public_key(key_id)
    try:
        sig_bytes = bytes.fromhex(signature_hex)
        public_key.verify(sig_bytes, canonical_payload.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError) as exc:
        raise SignatureVerificationError("Cryptographic signature verification failed.") from exc
