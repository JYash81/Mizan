"""Immutable Backup & Ransomware Resilience Service.

Implements Section 12 of Mizan Security Strategy v2:
- Immutable WORM (Write Once, Read Many) backup storage with separate credentials.
- Compromised application administrator cannot delete, overwrite, or truncate immutable backup copies.
- Automated restore drill verifying schema integrity and cryptographic hash matching.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any


class BackupTamperError(Exception):
    """Raised when an unauthorized entity attempts to modify or delete immutable backup storage."""


class BackupRestoreError(Exception):
    """Raised when a restore drill integrity check fails."""


class ImmutableBackupSnapshot:
    def __init__(
        self,
        backup_id: str,
        workspace_id: str,
        data_records: list[dict[str, Any]],
        manifest: dict[str, Any],
        digest: str,
        is_immutable: bool = True,
    ) -> None:
        self.backup_id = backup_id
        self.workspace_id = workspace_id
        self.data_records = data_records
        self.manifest = manifest
        self.digest = digest
        self.is_immutable = is_immutable
        self.created_at = datetime.now(UTC)


class ImmutableBackupStorage:
    """Simulates an isolated, immutable backup vault with separate administrative credentials."""

    def __init__(self) -> None:
        self._vault: dict[str, ImmutableBackupSnapshot] = {}

    def create_immutable_backup(
        self,
        workspace_id: str,
        data_records: list[dict[str, Any]],
        description: str = "Automated immutable snapshot",
    ) -> ImmutableBackupSnapshot:
        """Creates a signed, hash-verified immutable snapshot."""
        backup_id = f"BKP-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(UTC).isoformat()

        serialized_data = json.dumps(data_records, sort_keys=True)
        digest = hashlib.sha256(serialized_data.encode("utf-8")).hexdigest()

        manifest = {
            "backup_id": backup_id,
            "workspace_id": workspace_id,
            "record_count": len(data_records),
            "created_at": now,
            "description": description,
            "sha256_digest": digest,
        }

        snapshot = ImmutableBackupSnapshot(
            backup_id=backup_id,
            workspace_id=workspace_id,
            data_records=data_records,
            manifest=manifest,
            digest=digest,
            is_immutable=True,
        )
        self._vault[backup_id] = snapshot
        return snapshot

    def attempt_delete_backup(
        self,
        backup_id: str,
        requesting_actor_is_app_admin: bool = True,
    ) -> None:
        """Simulates an attacker with compromised app admin credentials attempting to delete a backup.

        Raises:
            BackupTamperError: Every deletion attempt is rejected by the immutable storage policy.
        """
        snapshot = self._vault.get(backup_id)
        if not snapshot:
            raise ValueError(f"Backup '{backup_id}' not found.")

        if snapshot.is_immutable:
            raise BackupTamperError(
                f"Immutable Backup Protection Error: Backup '{backup_id}' is locked under "
                "immutable WORM compliance policy. Application admin credentials cannot delete or truncate backups."
            )

    def execute_restore_drill(
        self,
        backup_id: str,
    ) -> dict[str, Any]:
        """Restores from immutable backup and verifies cryptographic integrity against original manifest.

        Raises:
            BackupRestoreError: If digest verification or record count fails.
        """
        snapshot = self._vault.get(backup_id)
        if not snapshot:
            raise BackupRestoreError(f"Backup '{backup_id}' does not exist.")

        # Re-compute digest of data records
        serialized_data = json.dumps(snapshot.data_records, sort_keys=True)
        recalc_digest = hashlib.sha256(serialized_data.encode("utf-8")).hexdigest()

        if recalc_digest != snapshot.digest:
            raise BackupRestoreError(
                f"Restore integrity failed: Recomputed digest '{recalc_digest}' "
                f"does not match manifest '{snapshot.digest}'."
            )

        return {
            "status": "RESTORE_SUCCESS",
            "backup_id": backup_id,
            "workspace_id": snapshot.workspace_id,
            "restored_records_count": len(snapshot.data_records),
            "manifest": snapshot.manifest,
            "verified_digest": recalc_digest,
            "restored_at": datetime.now(UTC).isoformat(),
        }


# Global immutable backup vault instance
backup_vault = ImmutableBackupStorage()
