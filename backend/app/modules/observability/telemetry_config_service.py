"""Telemetry configuration and explicit sync consent management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import TelemetryConfiguration
from app.modules.observability.schemas import (
    TelemetryConfigurationRead,
    TelemetryConsentUpdateRequest,
)


def get_or_create_telemetry_config(
    db: Session,
    customer_site_id: str,
) -> TelemetryConfigurationRead:
    """Retrieve or initialize customer site telemetry configuration."""
    config = db.execute(
        select(TelemetryConfiguration).where(TelemetryConfiguration.customer_site_id == customer_site_id)
    ).scalar_one_or_none()

    if not config:
        config = TelemetryConfiguration(
            customer_site_id=customer_site_id,
            sync_consent=False,  # Strict default: Customer-local first
            retention_days=30,
            metrics_enabled=True,
            events_enabled=True,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return _to_config_read(config)


def update_telemetry_consent(
    db: Session,
    customer_site_id: str,
    payload: TelemetryConsentUpdateRequest,
    actor_id: str,
) -> TelemetryConfigurationRead:
    """Update customer opt-in consent for centralized telemetry synchronization."""
    config = db.execute(
        select(TelemetryConfiguration).where(TelemetryConfiguration.customer_site_id == customer_site_id)
    ).scalar_one_or_none()

    now = datetime.now(UTC)

    if not config:
        config = TelemetryConfiguration(
            customer_site_id=customer_site_id,
            sync_consent=payload.sync_consent,
            consent_granted_by=actor_id if payload.sync_consent else None,
            consent_granted_at=now if payload.sync_consent else None,
            consent_expires_at=now + timedelta(days=365) if payload.sync_consent else None,
            retention_days=payload.retention_days,
            metrics_enabled=True,
            events_enabled=True,
        )
        db.add(config)
    else:
        config.sync_consent = payload.sync_consent
        config.retention_days = payload.retention_days
        if payload.sync_consent:
            config.consent_granted_by = actor_id
            config.consent_granted_at = now
            config.consent_expires_at = now + timedelta(days=365)
        else:
            config.consent_granted_by = None
            config.consent_granted_at = None
            config.consent_expires_at = None
        config.updated_at = now

    db.commit()
    db.refresh(config)
    return _to_config_read(config)


def _to_config_read(c: TelemetryConfiguration) -> TelemetryConfigurationRead:
    return TelemetryConfigurationRead(
        id=c.id,
        customer_site_id=c.customer_site_id,
        sync_consent=c.sync_consent,
        consent_granted_by=c.consent_granted_by,
        consent_granted_at=c.consent_granted_at,
        consent_expires_at=c.consent_expires_at,
        retention_days=c.retention_days,
        metrics_enabled=c.metrics_enabled,
        events_enabled=c.events_enabled,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )
