"""Sentinel Decide Component: Deterministic Policy Evaluation and Order Signing.

Enforces:
1. No direct execution authority (execution belongs to local runtime enforcer).
2. No direct reading of customer data content.
3. Per-tenant blast radius limits (caps containment actions per rolling time window).
4. Dual human approval requirement for cross-tenant containment.
5. Ed25519 cryptographic signing with purpose 'SENTINEL_CONTAINMENT_ORDER'.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sentinel import (
    OrderExecutionStatus,
    SentinelContainmentOrder,
)
from app.modules.masking.cryptography.signing_service import (
    sign_payload,
)
from app.modules.sentinel.exceptions import (
    BlastRadiusLimitExceededError,
    ComponentBoundaryViolationError,
    DualApprovalRequiredError,
)
from app.modules.sentinel.schemas import (
    ContainmentOrderCreate,
    ContainmentOrderRead,
)

# Blast radius configuration: max 5 automated containment orders per 10 minutes per tenant
DEFAULT_BLAST_RADIUS_WINDOW_MINUTES = 10
DEFAULT_MAX_ACTIONS_PER_WINDOW = 5
SENTINEL_SIGNING_KEY_ID = "sentinel_decide_key"
CONTAINMENT_PURPOSE = "SENTINEL_CONTAINMENT_ORDER"


def evaluate_and_issue_containment_order(
    db: Session,
    payload: ContainmentOrderCreate,
    max_actions_per_window: int = DEFAULT_MAX_ACTIONS_PER_WINDOW,
    window_minutes: int = DEFAULT_BLAST_RADIUS_WINDOW_MINUTES,
) -> ContainmentOrderRead:
    """Evaluates policy and issues a signed, scoped containment order.

    Raises:
        DualApprovalRequiredError: If cross-tenant action lacks two distinct approvers.
        BlastRadiusLimitExceededError: If tenant action rate exceeds limit.
    """
    now = datetime.now(UTC)

    # Cross-tenant containment guard: requires dual human approval
    if payload.is_cross_tenant:
        if (
            not payload.approver_1_id
            or not payload.approver_2_id
            or payload.approver_1_id == payload.approver_2_id
            or not payload.dual_approval_token
        ):
            raise DualApprovalRequiredError(
                "Cross-tenant containment orders require two distinct authorized human approvers and offline authorization."
            )

    # Per-tenant blast-radius check: count orders in rolling window
    cutoff = now - timedelta(minutes=window_minutes)
    order_count_query = (
        select(func.count(SentinelContainmentOrder.id))
        .where(SentinelContainmentOrder.workspace_id == payload.workspace_id)
        .where(SentinelContainmentOrder.issued_at >= cutoff)
    )
    current_count = db.execute(order_count_query).scalar_one() or 0
    if current_count >= max_actions_per_window and not payload.is_cross_tenant:
        raise BlastRadiusLimitExceededError(
            f"Tenant {payload.workspace_id} reached blast radius limit of "
            f"{max_actions_per_window} containment actions per {window_minutes} minutes."
        )

    order_id = f"ORD-{secrets.token_hex(8).upper()}"
    nonce = secrets.token_hex(16)
    expires_at = now + timedelta(minutes=payload.duration_minutes)

    canonical_data: dict[str, Any] = {
        "action": payload.action.value,
        "expires_at": expires_at.isoformat(),
        "is_cross_tenant": payload.is_cross_tenant,
        "issued_at": now.isoformat(),
        "nonce": nonce,
        "order_id": order_id,
        "purpose": CONTAINMENT_PURPOSE,
        "reason": payload.reason,
        "target_id": payload.target_id,
        "target_type": payload.target_type.value,
        "workspace_id": payload.workspace_id,
    }

    canonical_str, signature_hex, signer_key = sign_payload(
        canonical_data, key_id=SENTINEL_SIGNING_KEY_ID
    )

    order = SentinelContainmentOrder(
        order_id=order_id,
        workspace_id=payload.workspace_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        action=payload.action,
        reason=payload.reason,
        issued_at=now,
        expires_at=expires_at,
        nonce=nonce,
        is_cross_tenant=payload.is_cross_tenant,
        dual_approved=bool(payload.approver_1_id and payload.approver_2_id),
        approver_1_id=payload.approver_1_id,
        approver_2_id=payload.approver_2_id,
        signature=signature_hex,
        canonical_payload=canonical_str,
        signature_purpose=CONTAINMENT_PURPOSE,
        signer_key_id=signer_key,
        execution_status=OrderExecutionStatus.PENDING,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return ContainmentOrderRead.model_validate(order)


def assert_decide_component_cannot_execute(action_name: str) -> None:
    """Security assertion: Decide component must never execute containment orders directly."""
    raise ComponentBoundaryViolationError(
        f"Sentinel Decide component cannot execute '{action_name}'. "
        "Execution authority belongs exclusively to the Act (local runtime enforcer) component."
    )


def assert_decide_component_cannot_read_tenant_content() -> None:
    """Security assertion: Decide component must never read raw customer dataset/content."""
    raise ComponentBoundaryViolationError(
        "Sentinel Decide component cannot read raw customer data content. "
        "It evaluates only metadata, policy rules, and correlated incident signals."
    )
