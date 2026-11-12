"""Support Access Broker: Just-In-Time Credential Issuance and Session Auditing.

Implements Section 9 of Mizan Security Strategy v2:
- Zero standing access for Mizan staff to customer tenant environments.
- Customer administrator explicit approval for scope and duration.
- Dual approval (second Mizan security approver) required for Restricted Data access.
- Auto-expiring, single-purpose tokens.
- Real-time customer-visible session logging.
- Instant customer revocation capability.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import User
from app.models.organization import WorkspaceMembership, WorkspaceRole
from app.models.sentinel import (
    SupportAccessRequest,
    SupportAccessScope,
    SupportAccessStatus,
    SupportSessionLog,
)
from app.modules.sentinel.exceptions import (
    DualApprovalRequiredError,
    SupportAccessDeniedError,
    SupportAccessExpiredError,
    TenantScopeMismatchError,
)
from app.modules.sentinel.schemas import (
    SupportAccessCreateRequest,
    SupportAccessRead,
    SupportSessionLogRead,
)


def request_support_access(
    db: Session,
    workspace_id: str,
    staff_user_id: str,
    payload: SupportAccessCreateRequest,
) -> SupportAccessRead:
    """Creates a new pending support access request."""
    # Ensure staff user exists
    staff_user = db.execute(select(User).where(User.id == staff_user_id)).scalar_one_or_none()
    if not staff_user:
        raise ValueError(f"Staff user '{staff_user_id}' not found.")

    req = SupportAccessRequest(
        workspace_id=workspace_id,
        ticket_id=payload.ticket_id,
        reason=payload.reason,
        requested_by_staff_id=staff_user_id,
        requested_scope=payload.requested_scope,
        duration_minutes=payload.duration_minutes,
        status=SupportAccessStatus.PENDING,
        is_break_glass=payload.is_break_glass,
        break_glass_reason=payload.break_glass_reason,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return SupportAccessRead.model_validate(req)


def approve_support_access(
    db: Session,
    request_id: str,
    customer_admin_id: str,
    second_mizan_approver_id: str | None = None,
) -> SupportAccessRead:
    """Customer administrator approves JIT access.

    Raises:
        SupportAccessDeniedError: If approver is not a workspace Owner/Admin.
        DualApprovalRequiredError: If Restricted data access lacks second approver.
    """
    req = db.execute(
        select(SupportAccessRequest).where(SupportAccessRequest.id == request_id)
    ).scalar_one_or_none()
    if not req:
        raise ValueError(f"Support access request '{request_id}' not found.")

    if req.status != SupportAccessStatus.PENDING:
        raise SupportAccessDeniedError(f"Request is not pending (current: {req.status.value}).")

    # Verify customer administrator authority
    membership = db.execute(
        select(WorkspaceMembership)
        .where(WorkspaceMembership.workspace_id == req.workspace_id)
        .where(WorkspaceMembership.user_id == customer_admin_id)
    ).scalar_one_or_none()

    if not membership or membership.role not in (
        WorkspaceRole.WORKSPACE_OWNER,
        WorkspaceRole.WORKSPACE_ADMIN,
    ):
        raise SupportAccessDeniedError(
            f"User '{customer_admin_id}' is not an authorized Owner or Admin for workspace '{req.workspace_id}'."
        )

    # Restricted data requires a second Mizan approver (Security Officer)
    if req.requested_scope == SupportAccessScope.RESTRICTED_DATA_DEBUG:
        if not second_mizan_approver_id or second_mizan_approver_id == req.requested_by_staff_id:
            raise DualApprovalRequiredError(
                "Access to Restricted Data requires a second distinct Mizan Security Officer approver."
            )

    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=req.duration_minutes)
    jit_token = f"jit_sec_{secrets.token_urlsafe(32)}"

    req.status = SupportAccessStatus.APPROVED
    req.approved_by_customer_id = customer_admin_id
    req.approved_at = now
    req.second_approver_id = second_mizan_approver_id
    req.second_approved_at = now if second_mizan_approver_id else None
    req.token_id = jit_token
    req.expires_at = expires_at

    db.commit()
    db.refresh(req)

    return SupportAccessRead.model_validate(req)


def verify_and_log_support_session(
    db: Session,
    token_id: str,
    workspace_id: str,
    action: str,
    resource: str,
    request_method: str = "GET",
    path: str = "/api/v1/support",
    status_code: int = 200,
) -> SupportSessionLogRead:
    """Validates JIT support token and writes a customer-visible real-time audit log."""
    req = db.execute(
        select(SupportAccessRequest).where(SupportAccessRequest.token_id == token_id)
    ).scalar_one_or_none()

    now = datetime.now(UTC)

    if not req:
        raise SupportAccessDeniedError("Invalid or non-existent JIT support token.")

    if req.status != SupportAccessStatus.APPROVED:
        raise SupportAccessExpiredError(f"Support access is {req.status.value}.")

    if req.workspace_id != workspace_id:
        raise TenantScopeMismatchError(
            f"JIT token for tenant '{req.workspace_id}' cannot be used on tenant '{workspace_id}'."
        )

    req_expires = req.expires_at
    if req_expires and req_expires.tzinfo is None:
        req_expires = req_expires.replace(tzinfo=UTC)

    if req_expires and now > req_expires:
        req.status = SupportAccessStatus.EXPIRED
        db.commit()
        raise SupportAccessExpiredError(f"Support access expired at {req.expires_at}.")

    # Record customer-visible session log
    session_log = SupportSessionLog(
        access_request_id=req.id,
        workspace_id=workspace_id,
        staff_user_id=req.requested_by_staff_id,
        action=action,
        resource=resource,
        request_method=request_method,
        path=path,
        status_code=status_code,
        timestamp=now,
    )
    db.add(session_log)
    db.commit()
    db.refresh(session_log)

    return SupportSessionLogRead.model_validate(session_log)


def revoke_support_access(
    db: Session,
    request_id: str,
    revoked_by_id: str,
) -> SupportAccessRead:
    """Allows customer administrator to instantly terminate support access."""
    req = db.execute(
        select(SupportAccessRequest).where(SupportAccessRequest.id == request_id)
    ).scalar_one_or_none()
    if not req:
        raise ValueError(f"Support access request '{request_id}' not found.")

    req.status = SupportAccessStatus.REVOKED
    db.commit()
    db.refresh(req)

    return SupportAccessRead.model_validate(req)


def list_support_requests(
    db: Session,
    workspace_id: str,
) -> list[SupportAccessRead]:
    """Lists support requests for a customer workspace."""
    requests = (
        db.execute(
            select(SupportAccessRequest)
            .where(SupportAccessRequest.workspace_id == workspace_id)
            .order_by(SupportAccessRequest.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [SupportAccessRead.model_validate(r) for r in requests]


def list_support_session_logs(
    db: Session,
    workspace_id: str,
    access_request_id: str | None = None,
) -> list[SupportSessionLogRead]:
    """Retrieves session logs for customer inspection."""
    query = select(SupportSessionLog).where(SupportSessionLog.workspace_id == workspace_id)
    if access_request_id:
        query = query.where(SupportSessionLog.access_request_id == access_request_id)
    logs = db.execute(query.order_by(SupportSessionLog.timestamp.desc())).scalars().all()
    return [SupportSessionLogRead.model_validate(log) for log in logs]
