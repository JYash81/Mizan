"""Authorized artifact download and distribution governance service."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.artifact_registry import ModelVersion, ModelVersionStatus, RegisteredArtifact
from app.models.catalog import (
    CatalogEvent,
    CatalogVisibility,
    DistributionStatus,
    ModelListing,
    PublicationStatus,
)
from app.modules.zoo.exceptions import (
    DownloadNotPermittedError,
    ListingNotFoundError,
    ListingNotPublishedError,
    RevokedReleaseError,
    UnapprovedReleaseError,
)


class ArtifactDownloadService:
    """Enforces strict multi-tier verification before permitting model artifact downloads."""

    @classmethod
    def authorize_artifact_download(
        cls,
        db: Session,
        listing_id: str,
        artifact_id: str,
        user_id: str,
        user_workspace_id: str | None = None,
        user_organization_id: str | None = None,
    ) -> dict[str, Any]:
        """Authorize a download request for a registered artifact."""
        listing = db.query(ModelListing).filter(ModelListing.id == listing_id).first()
        if not listing:
            raise ListingNotFoundError(f"Model listing {listing_id} not found.")

        # 1. Visibility check
        if listing.visibility == CatalogVisibility.WORKSPACE:
            if not user_workspace_id or user_workspace_id != listing.workspace_id:
                raise DownloadNotPermittedError("Listing is restricted to its owning workspace.")
        elif listing.visibility == CatalogVisibility.ORGANIZATION:
            if not user_organization_id or user_organization_id != listing.organization_id:
                raise DownloadNotPermittedError("Listing is restricted to its owning organization.")

        # 2. Publication status check
        if listing.publication_status != PublicationStatus.PUBLISHED:
            raise ListingNotPublishedError(f"Listing is in {listing.publication_status.value} state and not published.")

        # 3. Distribution status check
        if listing.distribution_status == DistributionStatus.METADATA_ONLY:
            raise DownloadNotPermittedError(
                "This model listing is designated as METADATA_ONLY. Binary downloads are not permitted by publisher."
            )
        if listing.distribution_status in {DistributionStatus.RESTRICTED, DistributionStatus.UNAVAILABLE}:
            raise DownloadNotPermittedError(
                f"Artifact downloads are currently {listing.distribution_status.value}."
            )

        # 4. Underlying M11 release status revalidation
        model_version: ModelVersion = listing.model_version
        if not model_version:
            raise UnapprovedReleaseError("Listing has no linked model version.")

        if model_version.status == ModelVersionStatus.REVOKED:
            raise RevokedReleaseError(f"Underlying model release {model_version.version_tag} has been revoked.")
        if model_version.status != ModelVersionStatus.APPROVED:
            raise UnapprovedReleaseError(f"Underlying model release {model_version.version_tag} is in {model_version.status.value} state.")

        # Recheck Gate 3 approval
        approval = model_version.gate3_approval
        if not approval or approval.decision.value != "APPROVED":
            raise UnapprovedReleaseError("Model release lacks valid Gate 3 release approval.")

        # 5. Resolve target registered artifact
        artifact = (
            db.query(RegisteredArtifact)
            .filter(
                RegisteredArtifact.id == artifact_id,
                RegisteredArtifact.model_version_id == model_version.id,
            )
            .first()
        )
        if not artifact:
            raise DownloadNotPermittedError(f"Artifact {artifact_id} not found in model release.")

        # Log authorization event
        event = CatalogEvent(
            listing_type="MODEL",
            listing_id=listing.id,
            event_type="DOWNLOAD_AUTHORIZED",
            triggered_by_user_id=user_id,
            message=f"Artifact download authorized: {artifact.artifact_type.value} ({artifact.sha256[:12]}...)",
            metadata_json=json.dumps({
                "artifact_id": artifact.id,
                "sha256": artifact.sha256,
                "format": artifact.format,
                "file_size_bytes": artifact.file_size_bytes,
            }),
        )
        db.add(event)
        db.commit()

        return {
            "authorized": True,
            "listing_id": listing.id,
            "model_version_id": model_version.id,
            "artifact_id": artifact.id,
            "artifact_type": artifact.artifact_type.value,
            "format": artifact.format,
            "file_size_bytes": artifact.file_size_bytes,
            "sha256": artifact.sha256,
            "storage_reference": artifact.storage_reference,
            "download_filename": f"{listing.slug}-{artifact.id[:8]}.{artifact.format.lower()}",
        }
