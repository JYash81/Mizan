"""Model Zoo catalog service: publication governance, discovery, and detail retrieval."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.artifact_registry import ModelFamily, ModelVersion, ModelVersionStatus
from app.models.catalog import (
    CatalogEvent,
    CatalogReview,
    CatalogVisibility,
    DistributionStatus,
    HardwareCompatibilityBadge,
    HardwareCompatibilitySnapshot,
    ModelListing,
    PublicationStatus,
)
from app.modules.zoo.exceptions import (
    ListingNotFoundError,
    ListingReviewError,
    PublicPublicationNotAllowedError,
    RevokedReleaseError,
    UnapprovedReleaseError,
)
from app.modules.zoo.hardware_badge_service import HardwareBadgeService
from app.modules.zoo.installation_guide_service import InstallationGuideService
from app.modules.zoo.public_metadata_sanitizer import PublicMetadataSanitizer


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[-\s]+", "-", s).strip("-")


class ModelCatalogService:
    """Manages Model Zoo listings, publication lifecycle, discovery search, and detail projections."""

    @classmethod
    def create_model_listing(
        cls,
        db: Session,
        workspace_id: str,
        organization_id: str,
        user_id: str,
        model_version_id: str,
        title: str,
        description: str,
        slug: str | None = None,
        detailed_description: str | None = None,
        category: str = "GENERAL_CHAT",
        tags: list[str] | None = None,
        visibility: CatalogVisibility = CatalogVisibility.WORKSPACE,
        distribution_status: DistributionStatus = DistributionStatus.DOWNLOADABLE,
    ) -> ModelListing:
        """Create a new Model Zoo catalog entry for an approved M11 release."""
        model_version = (
            db.query(ModelVersion)
            .filter(ModelVersion.id == model_version_id, ModelVersion.workspace_id == workspace_id)
            .first()
        )
        if not model_version:
            raise ListingNotFoundError(f"Model version {model_version_id} not found in workspace.")

        # Revalidate M11 release status
        if model_version.status == ModelVersionStatus.REVOKED:
            raise RevokedReleaseError(f"Model version {model_version.version_tag} is revoked and cannot be listed.")
        if model_version.status != ModelVersionStatus.APPROVED:
            raise UnapprovedReleaseError(
                f"Model version {model_version.version_tag} has status {model_version.status.value}. Only APPROVED releases can be listed in the Model Zoo."
            )

        # Recheck Gate 3 approval
        approval = model_version.gate3_approval
        if not approval or approval.decision.value != "APPROVED":
            raise UnapprovedReleaseError("Model version lacks a valid Gate 3 release approval.")

        # Generate slug if omitted
        base_slug = slug or _slugify(title)
        final_slug = base_slug
        counter = 1
        while db.query(ModelListing).filter(ModelListing.workspace_id == workspace_id, ModelListing.slug == final_slug).first():
            final_slug = f"{base_slug}-{counter}"
            counter += 1

        listing = ModelListing(
            organization_id=organization_id,
            workspace_id=workspace_id,
            model_family_id=model_version.family_id,
            model_version_id=model_version.id,
            title=title.strip(),
            slug=final_slug,
            description=description.strip(),
            detailed_description=detailed_description.strip() if detailed_description else None,
            category=category,
            tags_json=json.dumps(tags or []),
            visibility=visibility,
            publication_status=PublicationStatus.DRAFT,
            distribution_status=distribution_status,
            created_by=user_id,
        )
        db.add(listing)
        db.flush()

        # Evaluate and record initial hardware compatibility snapshots
        eval_badges = HardwareBadgeService.evaluate_model_compatibility(
            db=db,
            model_version_id=model_version.id,
            min_ram_mb=model_version.min_ram_mb,
            min_vram_mb=model_version.min_vram_mb,
            target_hardware_key=model_version.target_hardware_key,
            artifact_digest=model_version.release_manifest_digest,
        )
        HardwareBadgeService.sync_snapshots(
            db=db,
            listing_type="MODEL",
            listing_id=listing.id,
            model_version_id=model_version.id,
            eval_results=eval_badges,
            artifact_digest=model_version.release_manifest_digest,
        )

        event = CatalogEvent(
            listing_type="MODEL",
            listing_id=listing.id,
            event_type="LISTING_CREATED",
            triggered_by_user_id=user_id,
            message=f"Model listing '{title}' created in DRAFT state.",
            metadata_json=json.dumps({"version_tag": model_version.version_tag, "slug": final_slug}),
        )
        db.add(event)
        db.commit()
        db.refresh(listing)
        return listing

    @classmethod
    def submit_for_review(cls, db: Session, listing_id: str, user_id: str) -> ModelListing:
        """Submit a draft model listing for catalog review."""
        listing = db.query(ModelListing).filter(ModelListing.id == listing_id).first()
        if not listing:
            raise ListingNotFoundError(f"Model listing {listing_id} not found.")

        if listing.publication_status not in {PublicationStatus.DRAFT, PublicationStatus.REJECTED}:
            raise ListingReviewError(f"Listing cannot be submitted from {listing.publication_status.value} state.")

        listing.publication_status = PublicationStatus.SUBMITTED_FOR_REVIEW
        event = CatalogEvent(
            listing_type="MODEL",
            listing_id=listing.id,
            event_type="LISTING_SUBMITTED",
            triggered_by_user_id=user_id,
            message="Model listing submitted for publication review.",
            metadata_json="{}",
        )
        db.add(event)
        db.commit()
        db.refresh(listing)
        return listing

    @classmethod
    def review_and_publish(
        cls,
        db: Session,
        listing_id: str,
        reviewer_id: str,
        decision: str,  # APPROVED or REJECTED
        rationale: str,
    ) -> ModelListing:
        """Review and publish (or reject) a submitted model listing."""
        listing = db.query(ModelListing).filter(ModelListing.id == listing_id).first()
        if not listing:
            raise ListingNotFoundError(f"Model listing {listing_id} not found.")

        if listing.publication_status != PublicationStatus.SUBMITTED_FOR_REVIEW:
            raise ListingReviewError(f"Listing is in {listing.publication_status.value} and not pending review.")

        model_version: ModelVersion = listing.model_version
        if not model_version or model_version.status != ModelVersionStatus.APPROVED:
            raise UnapprovedReleaseError("Cannot publish listing: underlying M11 release is not APPROVED.")

        # Record review decision
        review = CatalogReview(
            listing_type="MODEL",
            listing_id=listing.id,
            reviewer_id=reviewer_id,
            decision=decision,
            rationale=rationale,
            policy_snapshot_json=json.dumps({"visibility": listing.visibility.value, "distribution": listing.distribution_status.value}),
        )
        db.add(review)

        if decision == "APPROVED":
            # Rights and disclosure verification for PUBLIC listings
            if listing.visibility == CatalogVisibility.PUBLIC:
                prov_summary = model_version.provenance_summary
                license_details = prov_summary.get("checks", {}).get("BASE_MODEL_LICENSE", {}).get("details", {})
                comm_allowed = license_details.get("commercial_use", True)
                if not comm_allowed and listing.distribution_status == DistributionStatus.DOWNLOADABLE:
                    raise PublicPublicationNotAllowedError(
                        "Public publication with DOWNLOADABLE status is blocked because model license restricts commercial/redistribution rights."
                    )

            # Re-evaluate hardware badges
            eval_badges = HardwareBadgeService.evaluate_model_compatibility(
                db=db,
                model_version_id=model_version.id,
                min_ram_mb=model_version.min_ram_mb,
                min_vram_mb=model_version.min_vram_mb,
                target_hardware_key=model_version.target_hardware_key,
                artifact_digest=model_version.release_manifest_digest,
            )
            HardwareBadgeService.sync_snapshots(
                db=db,
                listing_type="MODEL",
                listing_id=listing.id,
                model_version_id=model_version.id,
                eval_results=eval_badges,
                artifact_digest=model_version.release_manifest_digest,
            )

            # Generate sanitized public snapshot and publication digest
            sanitized_payload, pub_digest = PublicMetadataSanitizer.sanitize_model_listing(
                listing, model_version, eval_badges
            )
            listing.public_metadata_snapshot_json = json.dumps(sanitized_payload)
            listing.publication_digest = pub_digest
            listing.publication_status = PublicationStatus.PUBLISHED
            listing.published_by = reviewer_id
            listing.published_at = datetime.now(UTC)

            event_msg = f"Model listing published: {listing.title} ({listing.visibility.value})"
        else:
            listing.publication_status = PublicationStatus.REJECTED
            event_msg = f"Model listing rejected by reviewer: {rationale}"

        event = CatalogEvent(
            listing_type="MODEL",
            listing_id=listing.id,
            event_type=f"LISTING_{decision}",
            triggered_by_user_id=reviewer_id,
            message=event_msg,
            metadata_json=json.dumps({"rationale": rationale}),
        )
        db.add(event)
        db.commit()
        db.refresh(listing)
        return listing

    @classmethod
    def suspend_listing(cls, db: Session, listing_id: str, user_id: str, reason: str) -> ModelListing:
        """Suspend a published listing."""
        listing = db.query(ModelListing).filter(ModelListing.id == listing_id).first()
        if not listing:
            raise ListingNotFoundError(f"Model listing {listing_id} not found.")

        listing.publication_status = PublicationStatus.SUSPENDED
        listing.distribution_status = DistributionStatus.UNAVAILABLE

        event = CatalogEvent(
            listing_type="MODEL",
            listing_id=listing.id,
            event_type="LISTING_SUSPENDED",
            triggered_by_user_id=user_id,
            message=f"Model listing suspended: {reason}",
            metadata_json=json.dumps({"reason": reason}),
        )
        db.add(event)
        db.commit()
        db.refresh(listing)
        return listing

    @classmethod
    def search_and_list_models(
        cls,
        db: Session,
        workspace_id: str | None = None,
        organization_id: str | None = None,
        query_text: str | None = None,
        category: str | None = None,
        visibility: CatalogVisibility | None = None,
        status: PublicationStatus | None = None,
        hardware_badge: HardwareCompatibilityBadge | None = None,
        is_public_only: bool = False,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ModelListing], int]:
        """Search and paginate Model Zoo listings with strict visibility and tenant boundaries."""
        stmt = db.query(ModelListing)

        # Scoping
        if is_public_only:
            stmt = stmt.filter(
                ModelListing.visibility == CatalogVisibility.PUBLIC,
                ModelListing.publication_status == PublicationStatus.PUBLISHED,
            )
        else:
            # Multi-scope discovery: public, organization-wide, or workspace-owned
            filters = [ModelListing.visibility == CatalogVisibility.PUBLIC]
            if organization_id:
                filters.append(
                    (ModelListing.organization_id == organization_id)
                    & (ModelListing.visibility == CatalogVisibility.ORGANIZATION)
                )
            if workspace_id:
                filters.append(ModelListing.workspace_id == workspace_id)
            stmt = stmt.filter(or_(*filters))

            if status:
                stmt = stmt.filter(ModelListing.publication_status == status)

        if visibility:
            stmt = stmt.filter(ModelListing.visibility == visibility)
        if category:
            stmt = stmt.filter(ModelListing.category == category)

        # Search filter
        if query_text and query_text.strip():
            q = f"%{query_text.strip()}%"
            stmt = stmt.filter(
                or_(
                    ModelListing.title.ilike(q),
                    ModelListing.description.ilike(q),
                    ModelListing.slug.ilike(q),
                    ModelListing.tags_json.ilike(q),
                )
            )

        # Hardware badge filter
        if hardware_badge:
            stmt = stmt.join(HardwareCompatibilitySnapshot, HardwareCompatibilitySnapshot.listing_id == ModelListing.id).filter(
                HardwareCompatibilitySnapshot.listing_type == "MODEL",
                HardwareCompatibilitySnapshot.compatibility_badge == hardware_badge,
            )

        total_count = stmt.count()

        # Sorting
        if sort_by == "title":
            order_col = ModelListing.title.asc() if sort_dir == "asc" else ModelListing.title.desc()
        else:
            order_col = ModelListing.created_at.asc() if sort_dir == "asc" else ModelListing.created_at.desc()

        items = stmt.order_by(order_col).offset((page - 1) * page_size).limit(min(page_size, 50)).all()
        return items, total_count

    @classmethod
    def get_model_listing_detail(cls, db: Session, listing_id: str) -> dict[str, Any]:
        """Retrieve full details of a Model Zoo listing including hardware snapshots and static installation snippets."""
        listing = db.query(ModelListing).filter(ModelListing.id == listing_id).first()
        if not listing:
            raise ListingNotFoundError(f"Model listing {listing_id} not found.")

        model_version: ModelVersion = listing.model_version
        family: ModelFamily = listing.model_family

        # Fetch hardware snapshots
        snapshots = (
            db.query(HardwareCompatibilitySnapshot)
            .filter(
                HardwareCompatibilitySnapshot.listing_type == "MODEL",
                HardwareCompatibilitySnapshot.listing_id == listing.id,
            )
            .all()
        )
        badge_list = [
            {
                "hardware_profile_key": s.hardware_profile_key,
                "badge": s.compatibility_badge.value,
                "evidence_type": s.evidence_type,
                "metrics": s.metrics,
                "limitations_notes": s.limitations_notes,
                "source_reference": s.source_reference,
            }
            for s in snapshots
        ]

        # Generate static installation snippets
        snippets = InstallationGuideService.generate_model_snippets(listing, model_version)

        # Version history for this model family
        all_family_versions = (
            db.query(ModelVersion)
            .filter(ModelVersion.family_id == family.id)
            .order_by(ModelVersion.created_at.desc())
            .all()
        )
        history = [
            {
                "version_tag": v.version_tag,
                "status": v.status.value,
                "created_at": v.created_at.isoformat(),
                "release_manifest_digest": v.release_manifest_digest,
                "is_current": v.id == model_version.id,
            }
            for v in all_family_versions
        ]

        return {
            "listing": listing,
            "model_version": model_version,
            "model_family": family,
            "hardware_badges": badge_list,
            "installation_snippets": snippets,
            "version_history": history,
        }
