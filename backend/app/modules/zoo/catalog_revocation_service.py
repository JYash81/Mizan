"""Revocation propagation engine for Mizan Model Zoo and App Zoo."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.artifact_registry import ModelVersion
from app.models.catalog import (
    AppListing,
    AppModelDependency,
    AppVersion,
    CatalogEvent,
    DistributionStatus,
    ModelListing,
    PublicationStatus,
)


class CatalogRevocationService:
    """Enforces cascading revocation and suspension across Model Zoo and App Zoo when M11 releases are revoked."""

    @classmethod
    def propagate_release_revocation(
        cls,
        db: Session,
        model_version_id: str,
        user_id: str,
        revocation_reason: str,
    ) -> dict[str, Any]:
        """Suspend model listings and dependent app listings when an underlying M11 release is revoked."""
        model_version = db.query(ModelVersion).filter(ModelVersion.id == model_version_id).first()
        if not model_version:
            return {"model_listings_suspended": 0, "app_listings_suspended": 0}

        suspended_models: list[str] = []
        suspended_apps: list[str] = []

        # 1. Suspend direct Model Zoo listings
        model_listings = (
            db.query(ModelListing)
            .filter(ModelListing.model_version_id == model_version_id)
            .all()
        )
        for ml in model_listings:
            if ml.publication_status in {
                PublicationStatus.PUBLISHED,
                PublicationStatus.SUBMITTED_FOR_REVIEW,
                PublicationStatus.PENDING_APPROVAL,
            }:
                ml.publication_status = PublicationStatus.SUSPENDED
                ml.distribution_status = DistributionStatus.UNAVAILABLE
                suspended_models.append(ml.id)

                event = CatalogEvent(
                    listing_type="MODEL",
                    listing_id=ml.id,
                    event_type="REVOCATION_PROPAGATED",
                    triggered_by_user_id=user_id,
                    message=f"Model Zoo listing suspended: underlying M11 release {model_version.version_tag} was revoked ({revocation_reason})",
                    metadata_json=json.dumps({"reason": revocation_reason, "model_version_id": model_version_id}),
                )
                db.add(event)

        # 2. Suspend dependent App Zoo versions and listings
        deps = (
            db.query(AppModelDependency)
            .filter(AppModelDependency.model_version_id == model_version_id)
            .all()
        )
        for dep in deps:
            app_ver = db.query(AppVersion).filter(AppVersion.id == dep.app_version_id).first()
            if app_ver:
                app_ver.status = "BLOCKED"

            app_listings = (
                db.query(AppListing)
                .filter(AppListing.app_version_id == dep.app_version_id)
                .all()
            )
            for al in app_listings:
                if al.publication_status in {
                    PublicationStatus.PUBLISHED,
                    PublicationStatus.SUBMITTED_FOR_REVIEW,
                    PublicationStatus.PENDING_APPROVAL,
                }:
                    al.publication_status = PublicationStatus.SUSPENDED
                    al.distribution_status = DistributionStatus.UNAVAILABLE
                    suspended_apps.append(al.id)

                    event = CatalogEvent(
                        listing_type="APP",
                        listing_id=al.id,
                        event_type="DEPENDENCY_REVOCATION_PROPAGATED",
                        triggered_by_user_id=user_id,
                        message=f"App Zoo listing suspended: dependent model release {model_version.version_tag} was revoked ({revocation_reason})",
                        metadata_json=json.dumps({"reason": revocation_reason, "model_version_id": model_version_id}),
                    )
                    db.add(event)

        db.commit()

        return {
            "model_version_id": model_version_id,
            "model_listings_suspended": len(suspended_models),
            "app_listings_suspended": len(suspended_apps),
            "suspended_model_ids": suspended_models,
            "suspended_app_ids": suspended_apps,
        }
