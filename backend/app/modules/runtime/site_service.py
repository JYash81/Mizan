"""Customer Site and Site Agent enrollment management service."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.runtime import (
    AgentCommandStatus,
    AgentIdentityStatus,
    CustomerSite,
    SiteAgentCommand,
    SiteAgentIdentity,
    SiteEnrollmentToken,
    SiteStatus,
)
from app.modules.runtime.exceptions import (
    AgentIdentityRevokedError,
    AgentNotEnrolledError,
    DuplicateSiteKeyError,
    EnrollmentTokenAlreadyConsumedError,
    EnrollmentTokenExpiredError,
    InvalidEnrollmentTokenError,
    SiteNotFoundError,
    SiteSuspendedOrRevokedError,
)
from app.modules.runtime.schemas import (
    CustomerSiteCreate,
    CustomerSiteRead,
    EnrollmentTokenCreateResponse,
    SiteAgentEnrollRequest,
    SiteAgentEnrollResponse,
    SiteAgentHeartbeatRequest,
    SiteAgentHeartbeatResponse,
)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def create_customer_site(
    db: Session,
    organization_id: str,
    workspace_id: str,
    payload: CustomerSiteCreate,
    user_id: str,
) -> CustomerSiteRead:
    """Create a new customer deployment site."""
    existing = db.execute(
        select(CustomerSite).where(
            CustomerSite.workspace_id == workspace_id,
            CustomerSite.site_key == payload.site_key,
        )
    ).scalar_one_or_none()

    if existing:
        raise DuplicateSiteKeyError(
            f"Site with key '{payload.site_key}' already exists in this workspace."
        )

    site = CustomerSite(
        organization_id=organization_id,
        workspace_id=workspace_id,
        site_key=payload.site_key,
        site_name=payload.site_name,
        description=payload.description,
        status=SiteStatus.ENROLLING,
        created_by=user_id,
    )
    db.add(site)
    db.commit()
    db.refresh(site)

    return _to_site_read(site)


def list_customer_sites(
    db: Session,
    workspace_id: str,
) -> list[CustomerSiteRead]:
    """List all customer deployment sites for a workspace."""
    sites = (
        db.execute(
            select(CustomerSite)
            .where(CustomerSite.workspace_id == workspace_id)
            .order_by(CustomerSite.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [_to_site_read(site) for site in sites]


def get_customer_site(
    db: Session,
    site_id: str,
    workspace_id: str | None = None,
) -> CustomerSite:
    """Retrieve customer site by ID, optionally verifying workspace isolation."""
    query = select(CustomerSite).where(CustomerSite.id == site_id)
    if workspace_id:
        query = query.where(CustomerSite.workspace_id == workspace_id)

    site = db.execute(query).scalar_one_or_none()
    if not site:
        raise SiteNotFoundError(f"Customer site '{site_id}' not found.")
    return site


def get_customer_site_read(
    db: Session,
    site_id: str,
    workspace_id: str | None = None,
) -> CustomerSiteRead:
    """Retrieve and format customer site."""
    site = get_customer_site(db, site_id, workspace_id)
    return _to_site_read(site)


def generate_enrollment_token(
    db: Session,
    site_id: str,
    user_id: str,
    expires_in_minutes: int = 60,
    workspace_id: str | None = None,
) -> EnrollmentTokenCreateResponse:
    """Generate a single-use, high-entropy enrollment token for a customer site."""
    site = get_customer_site(db, site_id, workspace_id)

    if site.status in (SiteStatus.REVOKED, SiteStatus.SUSPENDED):
        raise SiteSuspendedOrRevokedError(
            f"Cannot generate enrollment token for site in status '{site.status}'."
        )

    # 256 bits of cryptographically secure random entropy
    raw_token = secrets.token_urlsafe(32)
    token_digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)

    token_record = SiteEnrollmentToken(
        customer_site_id=site.id,
        token_digest=token_digest,
        expires_at=expires_at,
        created_by=user_id,
    )
    db.add(token_record)
    db.commit()
    db.refresh(token_record)

    return EnrollmentTokenCreateResponse(
        token_id=token_record.id,
        raw_token=raw_token,
        expires_at=expires_at,
        site_id=site.id,
        site_key=site.site_key,
    )


def enroll_site_agent(
    db: Session,
    payload: SiteAgentEnrollRequest,
) -> SiteAgentEnrollResponse:
    """Complete enrollment of a customer site agent using a single-use token."""
    token_digest = hashlib.sha256(payload.token.strip().encode("utf-8")).hexdigest()

    token_record = db.execute(
        select(SiteEnrollmentToken).where(SiteEnrollmentToken.token_digest == token_digest)
    ).scalar_one_or_none()

    if not token_record:
        raise InvalidEnrollmentTokenError("Invalid enrollment token.")

    now = datetime.now(UTC)
    if token_record.consumed_at is not None:
        raise EnrollmentTokenAlreadyConsumedError("This enrollment token has already been consumed.")

    if _ensure_utc(token_record.expires_at) < now:
        raise EnrollmentTokenExpiredError("This enrollment token has expired.")

    site = db.execute(
        select(CustomerSite).where(CustomerSite.id == token_record.customer_site_id)
    ).scalar_one_or_none()

    if not site:
        raise SiteNotFoundError("Customer site associated with token does not exist.")

    if site.status in (SiteStatus.REVOKED, SiteStatus.SUSPENDED):
        raise SiteSuspendedOrRevokedError(
            f"Cannot enroll agent for site with status '{site.status}'."
        )

    # Fingerprint public key
    pk_fingerprint = hashlib.sha256(payload.public_key_pem.strip().encode("utf-8")).hexdigest()

    # Invalidate token
    token_record.consumed_at = now

    # Check if identity exists or create new
    identity = site.agent_identity
    if identity:
        identity.public_key_fingerprint = pk_fingerprint
        identity.key_id = payload.key_id
        identity.protocol_version = payload.protocol_version
        identity.agent_version = payload.agent_version
        identity.runtime_version = payload.runtime_version
        identity.platform_info_json = json.dumps(payload.platform_info)
        identity.status = AgentIdentityStatus.ACTIVE
        identity.enrolled_at = now
        identity.last_heartbeat_at = now
    else:
        identity = SiteAgentIdentity(
            customer_site_id=site.id,
            public_key_fingerprint=pk_fingerprint,
            key_id=payload.key_id,
            protocol_version=payload.protocol_version,
            agent_version=payload.agent_version,
            runtime_version=payload.runtime_version,
            platform_info_json=json.dumps(payload.platform_info),
            status=AgentIdentityStatus.ACTIVE,
            enrolled_at=now,
            last_heartbeat_at=now,
        )
        db.add(identity)

    site.status = SiteStatus.ACTIVE
    db.commit()
    db.refresh(identity)

    return SiteAgentEnrollResponse(
        agent_id=identity.agent_id,
        site_id=site.id,
        public_key_fingerprint=identity.public_key_fingerprint,
        enrolled_at=identity.enrolled_at,
        status=identity.status,
    )


def report_agent_heartbeat(
    db: Session,
    payload: SiteAgentHeartbeatRequest,
) -> SiteAgentHeartbeatResponse:
    """Process an outbound periodic heartbeat from an enrolled Site Agent."""
    identity = db.execute(
        select(SiteAgentIdentity).where(SiteAgentIdentity.agent_id == payload.agent_id)
    ).scalar_one_or_none()

    if not identity:
        raise AgentNotEnrolledError("Site agent identity not recognized.")

    if identity.status != AgentIdentityStatus.ACTIVE:
        raise AgentIdentityRevokedError(f"Agent identity status is '{identity.status}'.")

    site = identity.site
    if site.status in (SiteStatus.REVOKED, SiteStatus.SUSPENDED):
        raise SiteSuspendedOrRevokedError(f"Site is currently '{site.status}'.")

    now = datetime.now(UTC)
    identity.last_heartbeat_at = now
    identity.agent_version = payload.agent_version
    identity.runtime_version = payload.runtime_version
    if payload.platform_info:
        identity.platform_info_json = json.dumps(payload.platform_info)

    # Keep site ACTIVE if it was in OFFLINE state
    if site.status == SiteStatus.OFFLINE:
        site.status = SiteStatus.ACTIVE

    # Count pending commands
    pending_count = (
        db.execute(
            select(SiteAgentCommand).where(
                SiteAgentCommand.customer_site_id == site.id,
                SiteAgentCommand.status == AgentCommandStatus.PENDING,
            )
        )
        .scalars()
        .all()
    )

    db.commit()

    return SiteAgentHeartbeatResponse(
        status="OK",
        last_heartbeat_at=now,
        pending_commands_count=len(pending_count),
    )


def revoke_customer_site(
    db: Session,
    site_id: str,
    workspace_id: str | None = None,
) -> CustomerSiteRead:
    """Revoke a customer site and terminate all agent credentials."""
    site = get_customer_site(db, site_id, workspace_id)
    site.status = SiteStatus.REVOKED

    if site.agent_identity:
        site.agent_identity.status = AgentIdentityStatus.REVOKED

    # Expire any pending commands
    pending_commands = (
        db.execute(
            select(SiteAgentCommand).where(
                SiteAgentCommand.customer_site_id == site.id,
                SiteAgentCommand.status == AgentCommandStatus.PENDING,
            )
        )
        .scalars()
        .all()
    )
    for cmd in pending_commands:
        cmd.status = AgentCommandStatus.EXPIRED

    db.commit()
    db.refresh(site)
    return _to_site_read(site)


def _to_site_read(site: CustomerSite) -> CustomerSiteRead:
    """Helper to convert CustomerSite model to CustomerSiteRead schema."""
    agent_enrolled = site.agent_identity is not None and site.agent_identity.status == AgentIdentityStatus.ACTIVE
    runtime_ver = site.agent_identity.runtime_version if site.agent_identity else None
    last_hb = site.agent_identity.last_heartbeat_at if site.agent_identity else None

    return CustomerSiteRead(
        id=site.id,
        organization_id=site.organization_id,
        workspace_id=site.workspace_id,
        site_key=site.site_key,
        site_name=site.site_name,
        description=site.description,
        status=site.status,
        created_by=site.created_by,
        created_at=site.created_at,
        updated_at=site.updated_at,
        agent_enrolled=agent_enrolled,
        active_runtime_version=runtime_ver,
        last_heartbeat_at=last_hb,
    )
