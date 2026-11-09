"""Pricing catalog service and repository for infrastructure cost rates."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.hardware import PricingCatalogEntry
from app.modules.cost.schemas.cost import PricingCatalogCreate


class PricingCatalogService:
    """Manages infrastructure pricing entries with versioning and provenance tracking."""

    def list_entries(
        self,
        db: Session,
        provider_name: str | None = None,
        resource_type: str | None = None,
        catalog_version: str | None = None,
    ) -> list[PricingCatalogEntry]:
        """List pricing records with optional filtering."""
        query = db.query(PricingCatalogEntry)
        if provider_name:
            query = query.filter(PricingCatalogEntry.provider_name == provider_name)
        if resource_type:
            query = query.filter(PricingCatalogEntry.resource_type == resource_type)
        if catalog_version:
            query = query.filter(PricingCatalogEntry.catalog_version == catalog_version)
        return query.order_by(
            PricingCatalogEntry.provider_name, PricingCatalogEntry.instance_type
        ).all()

    def get_entry(
        self,
        db: Session,
        provider_name: str,
        instance_type: str,
        region: str = "us-east-1",
        catalog_version: str = "2026.1",
    ) -> PricingCatalogEntry | None:
        """Find an exact pricing entry or return None if missing (never default to zero)."""
        return (
            db.query(PricingCatalogEntry)
            .filter(
                PricingCatalogEntry.provider_name == provider_name,
                PricingCatalogEntry.instance_type == instance_type,
                PricingCatalogEntry.region == region,
                PricingCatalogEntry.catalog_version == catalog_version,
            )
            .first()
        )

    def create_or_update_entry(
        self, db: Session, data: PricingCatalogCreate
    ) -> PricingCatalogEntry:
        """Create or update a pricing entry."""
        entry = self.get_entry(
            db,
            provider_name=data.provider_name,
            instance_type=data.instance_type,
            region=data.region,
            catalog_version=data.catalog_version,
        )
        now = datetime.now(UTC)
        if not entry:
            entry = PricingCatalogEntry(
                provider_name=data.provider_name,
                resource_type=data.resource_type,
                instance_type=data.instance_type,
                region=data.region,
                currency=data.currency,
                hourly_rate=data.hourly_rate,
                storage_monthly_rate_per_gb=data.storage_monthly_rate_per_gb,
                billing_unit_seconds=data.billing_unit_seconds,
                source_url=data.source_url,
                provenance=data.provenance,
                effective_from=now,
                is_verified=data.is_verified,
                catalog_version=data.catalog_version,
            )
            db.add(entry)
        else:
            entry.hourly_rate = data.hourly_rate
            entry.storage_monthly_rate_per_gb = data.storage_monthly_rate_per_gb
            entry.billing_unit_seconds = data.billing_unit_seconds
            entry.source_url = data.source_url
            entry.provenance = data.provenance
            entry.is_verified = data.is_verified
            entry.updated_at = now

        db.commit()
        db.refresh(entry)
        return entry
