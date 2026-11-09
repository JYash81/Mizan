"""Site Agent outbound polling, cryptographic command dispatch, and secure execution."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.runtime import (
    AgentCommandStatus,
    AgentCommandType,
    AgentIdentityStatus,
    CustomerSite,
    SiteAgentCommand,
    SiteAgentIdentity,
    SiteStatus,
)
from app.modules.masking.cryptography.signing_service import (
    SignatureVerificationError,
    canonicalize_payload,
    sign_payload,
    verify_signature,
)
from app.modules.runtime.exceptions import (
    AgentIdentityRevokedError,
    AgentNotEnrolledError,
    ExpiredCommandError,
    InvalidSignatureError,
    ReplayedNonceError,
    SiteNotFoundError,
    SiteSuspendedOrRevokedError,
    UnallowlistedCommandError,
)
from app.modules.runtime.schemas import (
    AgentCommandConsumeRequest,
    AgentCommandCreate,
    AgentCommandRead,
)

COMMAND_SIGNATURE_PURPOSE = "SITE_AGENT_COMMAND"


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def issue_agent_command(
    db: Session,
    customer_site_id: str,
    payload: AgentCommandCreate,
    expires_in_hours: int = 2,
    signing_key_id: str | None = None,
) -> AgentCommandRead:
    """Issue a signed, allowlisted command to a customer site agent."""
    site = db.execute(
        select(CustomerSite).where(CustomerSite.id == customer_site_id)
    ).scalar_one_or_none()

    if not site:
        raise SiteNotFoundError(f"Customer site '{customer_site_id}' not found.")

    if site.status in (SiteStatus.REVOKED, SiteStatus.SUSPENDED):
        raise SiteSuspendedOrRevokedError(f"Cannot dispatch commands to site with status '{site.status}'.")

    # Strict allowlist verification
    if payload.command_type not in AgentCommandType:
        raise UnallowlistedCommandError(f"Command '{payload.command_type}' is not allowlisted.")

    command_id = secrets.token_hex(16)
    nonce = secrets.token_hex(32)
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=expires_in_hours)

    canonical_command_payload = canonicalize_payload(payload.payload)
    payload_digest = hashlib.sha256(canonical_command_payload.encode("utf-8")).hexdigest()

    # Create signing envelope
    attestation_envelope: dict[str, Any] = {
        "command_id": command_id,
        "customer_site_id": site.id,
        "command_type": payload.command_type.value,
        "payload_digest": payload_digest,
        "nonce": nonce,
        "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": COMMAND_SIGNATURE_PURPOSE,
    }

    canonical_envelope, signature_hex, actual_key_id = sign_payload(
        payload=attestation_envelope,
        key_id=signing_key_id,
    )

    command = SiteAgentCommand(
        customer_site_id=site.id,
        command_id=command_id,
        command_type=payload.command_type,
        payload_json=json.dumps(payload.payload),
        payload_digest=payload_digest,
        nonce=nonce,
        issued_at=now,
        expires_at=expires_at,
        signature=signature_hex,
        status=AgentCommandStatus.PENDING,
    )
    db.add(command)
    db.commit()
    db.refresh(command)

    return _to_command_read(command)


def poll_pending_commands(
    db: Session,
    customer_site_id: str,
    agent_id: str,
) -> list[AgentCommandRead]:
    """Outbound poll endpoint for Site Agent to retrieve pending signed commands."""
    identity = db.execute(
        select(SiteAgentIdentity).where(
            SiteAgentIdentity.agent_id == agent_id,
            SiteAgentIdentity.customer_site_id == customer_site_id,
        )
    ).scalar_one_or_none()

    if not identity:
        raise AgentNotEnrolledError("Invalid agent or site mismatch.")

    if identity.status != AgentIdentityStatus.ACTIVE:
        raise AgentIdentityRevokedError(f"Agent identity status is '{identity.status}'.")

    now = datetime.now(UTC)

    # Check and expire stale commands
    stale_commands = (
        db.execute(
            select(SiteAgentCommand).where(
                SiteAgentCommand.customer_site_id == customer_site_id,
                SiteAgentCommand.status == AgentCommandStatus.PENDING,
                SiteAgentCommand.expires_at < now,
            )
        )
        .scalars()
        .all()
    )
    for cmd in stale_commands:
        cmd.status = AgentCommandStatus.EXPIRED

    # Fetch active pending commands
    active_commands = (
        db.execute(
            select(SiteAgentCommand).where(
                SiteAgentCommand.customer_site_id == customer_site_id,
                SiteAgentCommand.status == AgentCommandStatus.PENDING,
                SiteAgentCommand.expires_at >= now,
            ).order_by(SiteAgentCommand.issued_at.asc())
        )
        .scalars()
        .all()
    )

    for cmd in active_commands:
        cmd.status = AgentCommandStatus.DISPATCHED

    db.commit()
    return [_to_command_read(c) for c in active_commands]


def consume_agent_command(
    db: Session,
    customer_site_id: str,
    agent_id: str,
    payload: AgentCommandConsumeRequest,
    signing_key_id: str | None = None,
) -> dict[str, Any]:
    """Process execution acknowledgment from Site Agent and mark command CONSUMED."""
    identity = db.execute(
        select(SiteAgentIdentity).where(
            SiteAgentIdentity.agent_id == agent_id,
            SiteAgentIdentity.customer_site_id == customer_site_id,
        )
    ).scalar_one_or_none()

    if not identity or identity.status != AgentIdentityStatus.ACTIVE:
        raise AgentNotEnrolledError("Unrecognized or inactive agent identity.")

    command = db.execute(
        select(SiteAgentCommand).where(
            SiteAgentCommand.command_id == payload.command_id,
            SiteAgentCommand.customer_site_id == customer_site_id,
        )
    ).scalar_one_or_none()

    if not command:
        raise ExpiredCommandError("Command not found.")

    if command.status == AgentCommandStatus.CONSUMED:
        raise ReplayedNonceError("Command has already been consumed (replay attack detected).")

    now = datetime.now(UTC)
    if _ensure_utc(command.expires_at) < now:
        command.status = AgentCommandStatus.EXPIRED
        db.commit()
        raise ExpiredCommandError("Command has expired.")

    # Re-verify Ed25519 signature before recording consumption
    attestation_envelope = {
        "command_id": command.command_id,
        "customer_site_id": command.customer_site_id,
        "command_type": command.command_type.value,
        "payload_digest": command.payload_digest,
        "nonce": command.nonce,
        "expires_at": _ensure_utc(command.expires_at).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": COMMAND_SIGNATURE_PURPOSE,
    }
    canonical_envelope = canonicalize_payload(attestation_envelope)

    # Use default signing key if not specified
    from app.core.config import get_settings
    key_to_use = signing_key_id or get_settings().default_signing_key_id

    try:
        verify_signature(
            canonical_payload=canonical_envelope,
            signature_hex=command.signature,
            key_id=key_to_use,
        )
    except SignatureVerificationError as err:
        raise InvalidSignatureError(f"Command signature verification failed: {err}") from err

    command.status = payload.status
    command.consumed_at = now
    db.commit()

    return {
        "command_id": command.command_id,
        "status": command.status.value,
        "consumed_at": now.isoformat(),
    }


def _to_command_read(cmd: SiteAgentCommand) -> AgentCommandRead:
    return AgentCommandRead(
        id=cmd.id,
        command_id=cmd.command_id,
        customer_site_id=cmd.customer_site_id,
        command_type=cmd.command_type,
        payload=cmd.payload,
        payload_digest=cmd.payload_digest,
        nonce=cmd.nonce,
        issued_at=cmd.issued_at,
        expires_at=cmd.expires_at,
        signature=cmd.signature,
        status=cmd.status,
    )
