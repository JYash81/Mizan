"""Fail-Behaviour Matrix Engine & Local Encrypted Event Queue.

Implements Section 5 of Mizan Security Strategy v2:
- Principle: Protect confidentiality first, keep low-risk local work running within bounded policy age.
- Deterministic matrix evaluating 8 protected operations against 5 failure states.
- Local encrypted, hash-chained, bounded event queue for network cuts and Sentinel outages.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.modules.sentinel.schemas import (
    DependencyStatusInput,
    FailBehaviourEvaluateResponse,
)


class ProtectedOperation:
    EXTERNAL_TRANSFER_CONFIDENTIAL = "EXTERNAL_TRANSFER_CONFIDENTIAL"
    EXTERNAL_TRANSFER_PUBLIC = "EXTERNAL_TRANSFER_PUBLIC"
    LOCAL_INFERENCE_APPROVED_MODEL = "LOCAL_INFERENCE_APPROVED_MODEL"
    NEW_DATA_UPLOAD = "NEW_DATA_UPLOAD"
    MODEL_PACKAGE_INSTALL_OR_UPDATE = "MODEL_PACKAGE_INSTALL_OR_UPDATE"
    ADMIN_OR_POLICY_CHANGE = "ADMIN_OR_POLICY_CHANGE"
    AGENT_HIGH_IMPACT_TOOL_CALL = "AGENT_HIGH_IMPACT_TOOL_CALL"
    AGENT_LOW_IMPACT_TOOL_CALL = "AGENT_LOW_IMPACT_TOOL_CALL"


def evaluate_fail_behaviour(
    operation: str,
    dependencies: DependencyStatusInput,
    is_data_classified_public: bool = False,
    is_cached_policy_valid: bool = True,
    policy_age_hours: float = 1.0,
    max_policy_age_hours: float = 24.0,
    is_cached_key_valid: bool = True,
    is_tool_allowlisted: bool = True,
    is_within_budget: bool = True,
    is_local_tool: bool = True,
) -> FailBehaviourEvaluateResponse:
    """Evaluates the deterministic fail-behaviour matrix for an operation under dependency failures."""
    op = operation.upper()

    any_failure = (
        dependencies.policy_engine_down
        or dependencies.classifier_down
        or dependencies.sentinel_unreachable
        or dependencies.key_service_down
        or dependencies.network_cut
    )

    # 1. External transfer of Confidential / Restricted data: Fail closed on all
    if op == ProtectedOperation.EXTERNAL_TRANSFER_CONFIDENTIAL:
        if any_failure:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="FAIL_CLOSED",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="External transfer of Confidential/Restricted data fails closed on any dependency outage.",
            )
        return FailBehaviourEvaluateResponse(
            operation=op,
            allowed=True,
            action="ALLOW",
            quarantined=False,
            queued_telemetry=False,
            degraded_read_only=False,
            reason="All security dependencies operational; transfer permitted under active policy.",
        )

    # 2. External transfer of Public data
    if op == ProtectedOperation.EXTERNAL_TRANSFER_PUBLIC:
        # Classifier down: Allow ONLY data already classified Public; unclassified/new data is quarantined/blocked
        if dependencies.classifier_down and not is_data_classified_public:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="QUARANTINE_BLOCKED",
                quarantined=True,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="Classifier down: unclassified, new, or changed data is quarantined/blocked.",
            )

        if dependencies.network_cut:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="QUEUE",
                quarantined=False,
                queued_telemetry=True,
                degraded_read_only=False,
                reason="Network cut: transfer queued in local encrypted buffer until link recovery.",
            )

        if dependencies.policy_engine_down:
            if is_cached_policy_valid and policy_age_hours <= max_policy_age_hours:
                return FailBehaviourEvaluateResponse(
                    operation=op,
                    allowed=True,
                    action="ALLOW_LOGGED",
                    quarantined=False,
                    queued_telemetry=False,
                    degraded_read_only=False,
                    reason="Policy engine down: allowed under unexpired signed cached policy (logged).",
                )
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="REJECT_EXPIRED_POLICY",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="Policy engine down and cached policy expired; transfer rejected.",
            )

        if dependencies.key_service_down:
            if is_cached_key_valid:
                return FailBehaviourEvaluateResponse(
                    operation=op,
                    allowed=True,
                    action="ALLOW_CACHED_KEY",
                    quarantined=False,
                    queued_telemetry=False,
                    degraded_read_only=False,
                    reason="Key service down: allowed under verified cached key.",
                )
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="REJECT_NO_KEY",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="Key service down and no valid cached key; transfer rejected.",
            )

        # Sentinel unreachable or all healthy
        return FailBehaviourEvaluateResponse(
            operation=op,
            allowed=True,
            action="ALLOW_LOGGED",
            quarantined=False,
            queued_telemetry=dependencies.sentinel_unreachable,
            degraded_read_only=False,
            reason="Public data transfer allowed under verified policy (logged).",
        )

    # 3. Local inference on approved model
    if op == ProtectedOperation.LOCAL_INFERENCE_APPROVED_MODEL:
        degraded = policy_age_hours > max_policy_age_hours

        if dependencies.policy_engine_down:
            if degraded:
                return FailBehaviourEvaluateResponse(
                    operation=op,
                    allowed=False,
                    action="DEGRADE_READ_ONLY",
                    quarantined=False,
                    queued_telemetry=False,
                    degraded_read_only=True,
                    reason=f"Policy age ({policy_age_hours:.1f}h) exceeded tenant limit ({max_policy_age_hours:.1f}h); degraded to read-only.",
                )
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=True,
                action="RUN_LAST_SIGNED_POLICY",
                quarantined=False,
                queued_telemetry=dependencies.sentinel_unreachable or dependencies.network_cut,
                degraded_read_only=False,
                reason="Policy engine down: running on last signed policy within valid age window.",
            )

        if dependencies.key_service_down and not is_cached_key_valid:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="STOP_NO_VALID_KEY",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="Key service down and cached data key invalid; inference stopped.",
            )

        queued = dependencies.sentinel_unreachable or dependencies.network_cut
        return FailBehaviourEvaluateResponse(
            operation=op,
            allowed=True,
            action="RUN_FLAG_OUTPUTS" if dependencies.classifier_down else "RUN",
            quarantined=False,
            queued_telemetry=queued,
            degraded_read_only=False,
            reason="Local inference permitted; outputs flagged if classifier down, events queued if Sentinel unreachable/offline.",
        )

    # 4. New data upload
    if op == ProtectedOperation.NEW_DATA_UPLOAD:
        if dependencies.key_service_down or dependencies.network_cut:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="REJECT",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="New data upload rejected when key service is down or network is cut.",
            )
        if (
            dependencies.policy_engine_down
            or dependencies.classifier_down
            or dependencies.sentinel_unreachable
        ):
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="QUARANTINE_NO_PROCESSING",
                quarantined=True,
                queued_telemetry=dependencies.sentinel_unreachable,
                degraded_read_only=False,
                reason="Accepted to quarantine only; zero processing/classification until dependencies recover.",
            )
        return FailBehaviourEvaluateResponse(
            operation=op,
            allowed=True,
            action="ACCEPT_FOR_PROCESSING",
            quarantined=False,
            queued_telemetry=False,
            degraded_read_only=False,
            reason="All dependencies active: new data accepted for processing.",
        )

    # 5. Model package install or update: Reject on all dependency failures
    if op == ProtectedOperation.MODEL_PACKAGE_INSTALL_OR_UPDATE:
        if any_failure:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="REJECT",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="Model package install/update rejected during any dependency outage.",
            )
        return FailBehaviourEvaluateResponse(
            operation=op,
            allowed=True,
            action="ALLOW_INSTALL",
            quarantined=False,
            queued_telemetry=False,
            degraded_read_only=False,
            reason="Dependencies healthy; package verification proceeding.",
        )

    # 6. Admin or policy change: Reject on all dependency failures
    if op == ProtectedOperation.ADMIN_OR_POLICY_CHANGE:
        if any_failure:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="REJECT",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="Administrative or policy mutation rejected during any dependency outage.",
            )
        return FailBehaviourEvaluateResponse(
            operation=op,
            allowed=True,
            action="ALLOW_MUTATION",
            quarantined=False,
            queued_telemetry=False,
            degraded_read_only=False,
            reason="Dependencies healthy; admin mutation permitted.",
        )

    # 7. Agent high-impact tool call: Deny on all dependency failures
    if op == ProtectedOperation.AGENT_HIGH_IMPACT_TOOL_CALL:
        if any_failure:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="DENY",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="High-impact agent tool calls strictly denied during dependency outage.",
            )
        return FailBehaviourEvaluateResponse(
            operation=op,
            allowed=True,
            action="ALLOW_WITH_AUDIT",
            quarantined=False,
            queued_telemetry=False,
            degraded_read_only=False,
            reason="High-impact tool permitted under active policy and audited.",
        )

    # 8. Agent low-impact allowlisted tool
    if op == ProtectedOperation.AGENT_LOW_IMPACT_TOOL_CALL:
        if not is_tool_allowlisted or not is_within_budget:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="DENY_OUT_OF_SCOPE",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="Agent tool call not in allowlist or exceeded budget.",
            )
        if dependencies.network_cut and not is_local_tool:
            return FailBehaviourEvaluateResponse(
                operation=op,
                allowed=False,
                action="DENY_NON_LOCAL",
                quarantined=False,
                queued_telemetry=False,
                degraded_read_only=False,
                reason="Network cut: non-local tools denied.",
            )
        queued = dependencies.sentinel_unreachable or dependencies.network_cut
        return FailBehaviourEvaluateResponse(
            operation=op,
            allowed=True,
            action="RUN_WITHIN_BUDGET",
            quarantined=False,
            queued_telemetry=queued,
            degraded_read_only=False,
            reason="Low-impact tool permitted within budget; events queued if offline.",
        )

    # Default deny for any unknown operation
    return FailBehaviourEvaluateResponse(
        operation=op,
        allowed=False,
        action="DEFAULT_DENY",
        quarantined=False,
        queued_telemetry=False,
        degraded_read_only=False,
        reason=f"Operation '{operation}' not recognized; default deny enforced.",
    )


class LocalEncryptedEventQueue:
    """Tamper-evident, hash-chained, AES-GCM encrypted local queue for offline telemetry."""

    def __init__(self, queue_capacity: int = 1000, encryption_key: bytes | None = None) -> None:
        self.capacity = queue_capacity
        # 256-bit AES-GCM key
        self.key = encryption_key or AESGCM.generate_key(bit_length=256)
        self.aesgcm = AESGCM(self.key)
        self._queue: list[dict[str, Any]] = []
        self._last_event_hash = (
            "GENESIS_0000000000000000000000000000000000000000000000000000000000000000"
        )

    def enqueue_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Encodes, hash-chains, encrypts, and buffers an event."""
        if len(self._queue) >= self.capacity:
            raise BufferError(
                f"Local encrypted event queue reached maximum capacity ({self.capacity})."
            )

        now = datetime.now(UTC).isoformat()
        serialized_payload = json.dumps(payload, sort_keys=True)

        # Hash chain: SHA256(prev_hash + now + event_type + payload)
        chain_input = f"{self._last_event_hash}:{now}:{event_type}:{serialized_payload}"
        current_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()

        # Encrypt with AES-256-GCM
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(
            nonce, serialized_payload.encode("utf-8"), current_hash.encode("utf-8")
        )

        queue_entry = {
            "event_type": event_type,
            "timestamp": now,
            "prev_hash": self._last_event_hash,
            "event_hash": current_hash,
            "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8"),
        }

        self._queue.append(queue_entry)
        self._last_event_hash = current_hash
        return queue_entry

    def flush_and_verify(self) -> list[dict[str, Any]]:
        """Drains the queue in strict order, verifying the cryptographic hash chain and decrypting."""
        flushed_events: list[dict[str, Any]] = []
        expected_prev_hash = (
            "GENESIS_0000000000000000000000000000000000000000000000000000000000000000"
        )

        for entry in self._queue:
            # 1. Verify hash chain continuity
            if entry["prev_hash"] != expected_prev_hash:
                raise ValueError("Hash chain broken in local encrypted event queue!")

            # 2. Decrypt payload
            nonce = base64.b64decode(entry["nonce_b64"])
            ciphertext = base64.b64decode(entry["ciphertext_b64"])
            current_hash = entry["event_hash"]

            plaintext = self.aesgcm.decrypt(nonce, ciphertext, current_hash.encode("utf-8")).decode(
                "utf-8"
            )
            payload = json.loads(plaintext)

            # 3. Recalculate hash to verify integrity
            recalc_input = f"{expected_prev_hash}:{entry['timestamp']}:{entry['event_type']}:{json.dumps(payload, sort_keys=True)}"
            recalc_hash = hashlib.sha256(recalc_input.encode("utf-8")).hexdigest()
            if recalc_hash != current_hash:
                raise ValueError("Tampered event detected in local encrypted queue!")

            flushed_events.append(
                {
                    "event_type": entry["event_type"],
                    "timestamp": entry["timestamp"],
                    "event_hash": current_hash,
                    "payload": payload,
                }
            )
            expected_prev_hash = current_hash

        self._queue.clear()
        self._last_event_hash = expected_prev_hash
        return flushed_events

    def size(self) -> int:
        return len(self._queue)
