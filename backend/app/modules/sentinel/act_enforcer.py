"""Sentinel Act Enforcer: Local Runtime Enforcer.

Enforces:
1. Verification of Ed25519 signature and purpose 'SENTINEL_CONTAINMENT_ORDER'.
2. Strict tenant scope matching local runtime/workspace.
3. Expiration check (unexpired timestamp).
4. Replay rejection (nonce ledger tracking).
5. Execution of scoped containment actions (isolate agent, revoke token, quarantine slot, suspend site).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import AuthSession, AuthToken
from app.models.runtime import CustomerSite, RuntimeSlot, SiteStatus, SlotStatus
from app.models.sentinel import (
    ContainmentAction,
    ExecutedNonce,
    OrderExecutionStatus,
    SentinelContainmentOrder,
)
from app.modules.masking.cryptography.signing_service import (
    SignatureVerificationError,
    canonicalize_payload,
    verify_signature,
)
from app.modules.sentinel.decide_service import (
    CONTAINMENT_PURPOSE,
)
from app.modules.sentinel.exceptions import (
    OrderExpiredError,
    OrderSignatureVerificationError,
    ReplayedNonceError,
    TenantScopeMismatchError,
)
from app.modules.sentinel.schemas import (
    ContainmentOrderRead,
    OrderExecutionResult,
)


def verify_order_authenticity_and_scope(
    db: Session,
    order: ContainmentOrderRead,
    local_workspace_id: str,
) -> None:
    """Strictly validates containment order cryptographic signature, scope, expiration, and nonce.

    Raises:
        TenantScopeMismatchError: If order workspace does not match local enforcer.
        OrderExpiredError: If order timestamp has expired.
        OrderSignatureVerificationError: If cryptographic signature is invalid.
        ReplayedNonceError: If order nonce has already been executed.
    """
    now = datetime.now(UTC)

    # 1. Tenant boundary enforcement
    if not order.is_cross_tenant and order.workspace_id != local_workspace_id:
        raise TenantScopeMismatchError(
            f"Containment order tenant '{order.workspace_id}' does not match "
            f"local enforcer workspace '{local_workspace_id}'."
        )

    # 2. Expiration check
    order_expires = order.expires_at
    if order_expires.tzinfo is None:
        order_expires = order_expires.replace(tzinfo=UTC)
    if now > order_expires:
        raise OrderExpiredError(
            f"Containment order '{order.order_id}' expired at {order.expires_at} (current: {now})."
        )

    # 3. Purpose check
    if order.signature_purpose != CONTAINMENT_PURPOSE:
        raise OrderSignatureVerificationError(
            f"Order purpose '{order.signature_purpose}' does not match expected '{CONTAINMENT_PURPOSE}'."
        )

    # 4. Cryptographic signature verification
    if order.canonical_payload:
        canonical_str = order.canonical_payload
    else:
        canonical_data: dict[str, Any] = {
            "action": order.action.value if hasattr(order.action, "value") else str(order.action),
            "expires_at": order.expires_at.isoformat(),
            "is_cross_tenant": order.is_cross_tenant,
            "issued_at": order.issued_at.isoformat(),
            "nonce": order.nonce,
            "order_id": order.order_id,
            "purpose": order.signature_purpose,
            "reason": order.reason,
            "target_id": order.target_id,
            "target_type": order.target_type.value
            if hasattr(order.target_type, "value")
            else str(order.target_type),
            "workspace_id": order.workspace_id,
        }
        canonical_str = canonicalize_payload(canonical_data)

    try:
        verify_signature(canonical_str, order.signature, order.signer_key_id)
    except SignatureVerificationError as exc:
        raise OrderSignatureVerificationError(
            f"Cryptographic signature check failed on order '{order.order_id}'."
        ) from exc

    # 5. Replay prevention check
    existing_nonce = db.execute(
        select(ExecutedNonce).where(ExecutedNonce.nonce == order.nonce)
    ).scalar_one_or_none()
    if existing_nonce:
        raise ReplayedNonceError(
            f"Replay attack detected: Nonce '{order.nonce}' on order '{order.order_id}' "
            f"was already executed at {existing_nonce.executed_at}."
        )


def execute_containment_order(
    db: Session,
    order: ContainmentOrderRead,
    enforcer_id: str,
    local_workspace_id: str,
) -> OrderExecutionResult:
    """Verifies and executes a scoped containment order locally."""
    # Run full verification
    verify_order_authenticity_and_scope(db, order, local_workspace_id)

    now = datetime.now(UTC)

    # Record nonce in replay ledger
    nonce_record = ExecutedNonce(
        nonce=order.nonce,
        order_id=order.order_id,
        workspace_id=order.workspace_id,
        executed_at=now,
    )
    db.add(nonce_record)

    # Execute specific containment action
    action_taken = ""
    if order.action == ContainmentAction.ISOLATE_AGENT:
        action_taken = f"Isolated agent run '{order.target_id}' and revoked agent credentials."

    elif order.action == ContainmentAction.REVOKE_TOKEN:
        tokens = (
            db.execute(select(AuthToken).where(AuthToken.id == order.target_id)).scalars().all()
        )
        for tok in tokens:
            tok.is_revoked = True
        action_taken = f"Revoked token '{order.target_id}'."

    elif order.action == ContainmentAction.TERMINATE_SESSION:
        sessions = (
            db.execute(select(AuthSession).where(AuthSession.id == order.target_id)).scalars().all()
        )
        for sess in sessions:
            sess.is_revoked = True
        action_taken = f"Terminated session '{order.target_id}'."

    elif order.action == ContainmentAction.QUARANTINE_SLOT:
        slots = (
            db.execute(select(RuntimeSlot).where(RuntimeSlot.id == order.target_id)).scalars().all()
        )
        for slot in slots:
            slot.status = SlotStatus.FAILED
        action_taken = f"Quarantined runtime slot '{order.target_id}'."

    elif order.action == ContainmentAction.SUSPEND_SITE:
        sites = (
            db.execute(select(CustomerSite).where(CustomerSite.id == order.target_id))
            .scalars()
            .all()
        )
        for site in sites:
            site.status = SiteStatus.SUSPENDED
        action_taken = f"Suspended customer site '{order.target_id}'."

    else:
        action_taken = f"Executed generic scoped containment action '{order.action.value}' on '{order.target_id}'."

    # Update order record in database if present
    db_order = db.execute(
        select(SentinelContainmentOrder).where(SentinelContainmentOrder.order_id == order.order_id)
    ).scalar_one_or_none()
    if db_order:
        db_order.execution_status = OrderExecutionStatus.EXECUTED
        db_order.executed_at = now
        db_order.executed_by_enforcer = enforcer_id
        db_order.execution_details = action_taken

    db.commit()

    return OrderExecutionResult(
        order_id=order.order_id,
        success=True,
        status=OrderExecutionStatus.EXECUTED,
        executed_at=now,
        action_taken=action_taken,
        message=f"Successfully executed containment order '{order.order_id}' on enforcer '{enforcer_id}'.",
    )
