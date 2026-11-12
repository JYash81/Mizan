"""Key Hierarchy, Cryptographic Governance, and Revocation Service.

Implements Section 6 of Mizan Security Strategy v2:
- 5-Layer Key Hierarchy: Root of Trust -> Tenant Master Key -> Tenant Data Keys -> Signing Keys -> Service Credentials.
- BYOK / HYOK support abstraction.
- Key revocation with automatic rejection of stale/revoked keys.
- Scoped re-encryption of affected tenant data assets upon key compromise.
"""

from __future__ import annotations

import base64
import os
from datetime import UTC, datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.modules.sentinel.exceptions import KeyRevokedError


class KeyHierarchyLayer:
    ROOT_OF_TRUST = "ROOT_OF_TRUST"
    TENANT_MASTER_KEY = "TENANT_MASTER_KEY"
    TENANT_DATA_KEY = "TENANT_DATA_KEY"
    SIGNING_KEY = "SIGNING_KEY"
    SERVICE_CREDENTIAL = "SERVICE_CREDENTIAL"


class KeyRecord:
    def __init__(
        self,
        key_id: str,
        layer: str,
        workspace_id: str | None,
        data_class: str | None,
        raw_key_bytes: bytes,
        is_byok: bool = False,
    ) -> None:
        self.key_id = key_id
        self.layer = layer
        self.workspace_id = workspace_id
        self.data_class = data_class
        self.raw_key_bytes = raw_key_bytes
        self.is_byok = is_byok
        self.is_revoked = False
        self.revoked_at: datetime | None = None
        self.revocation_reason: str | None = None
        self.created_at = datetime.now(UTC)


class KeyGovernanceRegistry:
    """Manages cryptographic key lifecycle, hierarchy, and compromise response."""

    def __init__(self) -> None:
        self._keys: dict[str, KeyRecord] = {}

    def register_key(
        self,
        key_id: str,
        layer: str,
        workspace_id: str | None = None,
        data_class: str | None = None,
        is_byok: bool = False,
    ) -> KeyRecord:
        """Generates and registers a new cryptographic key under the governance hierarchy."""
        raw_bytes = AESGCM.generate_key(bit_length=256)
        rec = KeyRecord(
            key_id=key_id,
            layer=layer,
            workspace_id=workspace_id,
            data_class=data_class,
            raw_key_bytes=raw_bytes,
            is_byok=is_byok,
        )
        self._keys[key_id] = rec
        return rec

    def get_valid_key(self, key_id: str) -> KeyRecord:
        """Retrieves key and verifies it has not been revoked.

        Raises:
            KeyRevokedError: If key is revoked.
        """
        rec = self._keys.get(key_id)
        if not rec:
            # Dynamically register if default
            rec = self.register_key(key_id, KeyHierarchyLayer.TENANT_DATA_KEY)

        if rec.is_revoked:
            raise KeyRevokedError(
                f"Cryptographic key '{key_id}' was revoked on {rec.revoked_at} (Reason: {rec.revocation_reason}). "
                "Operation rejected."
            )
        return rec

    def revoke_key(self, key_id: str, reason: str) -> None:
        """Marks a compromised or retired key as revoked."""
        rec = self._keys.get(key_id)
        if rec:
            rec.is_revoked = True
            rec.revoked_at = datetime.now(UTC)
            rec.revocation_reason = reason

    def encrypt_with_tdk(self, key_id: str, plaintext: str) -> dict[str, str]:
        """Encrypts data using an active Tenant Data Key."""
        rec = self.get_valid_key(key_id)
        aesgcm = AESGCM(rec.raw_key_bytes)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), key_id.encode("utf-8"))
        return {
            "key_id": key_id,
            "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8"),
        }

    def decrypt_with_tdk(self, encrypted_record: dict[str, str]) -> str:
        """Decrypts data using the corresponding Tenant Data Key."""
        key_id = encrypted_record["key_id"]
        rec = self.get_valid_key(key_id)
        aesgcm = AESGCM(rec.raw_key_bytes)
        nonce = base64.b64decode(encrypted_record["nonce_b64"])
        ciphertext = base64.b64decode(encrypted_record["ciphertext_b64"])
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, key_id.encode("utf-8"))
        return plaintext_bytes.decode("utf-8")

    def reencrypt_data(
        self,
        encrypted_record: dict[str, str],
        new_key_id: str,
    ) -> dict[str, str]:
        """Re-encrypts data under a fresh key following revocation or rotation."""
        # Decrypt with old key (even if old key was marked compromised during the re-encryption job)
        old_key_id = encrypted_record["key_id"]
        old_rec = self._keys.get(old_key_id)
        if not old_rec:
            raise ValueError(f"Old key '{old_key_id}' not found.")

        aesgcm_old = AESGCM(old_rec.raw_key_bytes)
        nonce_old = base64.b64decode(encrypted_record["nonce_b64"])
        ciphertext_old = base64.b64decode(encrypted_record["ciphertext_b64"])
        plaintext_bytes = aesgcm_old.decrypt(nonce_old, ciphertext_old, old_key_id.encode("utf-8"))
        plaintext = plaintext_bytes.decode("utf-8")

        # Encrypt with new key
        return self.encrypt_with_tdk(new_key_id, plaintext)


# Global singleton instance for key governance
key_registry = KeyGovernanceRegistry()
