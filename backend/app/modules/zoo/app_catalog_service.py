"""App Zoo catalog service: app definitions, versioning, dependency governance, and discovery."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.artifact_registry import ModelVersion, ModelVersionStatus
from app.models.catalog import (
    AppDefinition,
    AppListing,
    AppModelDependency,
    AppVersion,
    CatalogEvent,
    CatalogReview,
    CatalogVisibility,
    DistributionStatus,
    HardwareCompatibilitySnapshot,
    PublicationStatus,
)
from app.modules.zoo.exceptions import (
    DependencyRevocationError,
    InvalidManifestError,
    ListingNotFoundError,
    ListingReviewError,
    UnapprovedReleaseError,
)
from app.modules.zoo.hardware_badge_service import HardwareBadgeService
from app.modules.zoo.installation_guide_service import InstallationGuideService
from app.modules.zoo.public_metadata_sanitizer import PublicMetadataSanitizer


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[-\s]+", "-", s).strip("-")


class AppCatalogService:
    """Manages App Zoo definitions, declarative versions, approved model dependencies, and catalog listings."""

    @classmethod
    def create_app_definition(
        cls,
        db: Session,
        workspace_id: str,
        organization_id: str,
        user_id: str,
        name: str,
        description: str,
        app_key: str | None = None,
        category: str = "DOCUMENT_ASSISTANT",
    ) -> AppDefinition:
        """Create a new application family namespace in the App Zoo."""
        key = app_key or _slugify(name)
        existing = db.query(AppDefinition).filter(
            AppDefinition.workspace_id == workspace_id,
            AppDefinition.app_key == key,
        ).first()
        if existing:
            raise InvalidManifestError(f"App definition with key '{key}' already exists in workspace.")

        app_def = AppDefinition(
            organization_id=organization_id,
            workspace_id=workspace_id,
            app_key=key,
            name=name.strip(),
            description=description.strip(),
            category=category,
            owner_id=user_id,
            status="ACTIVE",
        )
        db.add(app_def)
        db.commit()
        db.refresh(app_def)
        return app_def

    @classmethod
    def create_app_version(
        cls,
        db: Session,
        app_definition_id: str,
        user_id: str,
        version_tag: str,
        description: str | None = None,
        capabilities: list[str] | None = None,
        supported_input_types: list[str] | None = None,
        supported_output_types: list[str] | None = None,
        supported_languages: list[str] | None = None,
        license_id: str = "Apache-2.0",
        min_ram_mb: float = 4096.0,
        min_vram_mb: float = 0.0,
        target_hardware_key: str | None = None,
        model_dependencies: list[dict[str, str]] | None = None,
    ) -> AppVersion:
        """Create an immutable application package version bound to approved M11 model releases."""
        app_def = db.query(AppDefinition).filter(AppDefinition.id == app_definition_id).first()
        if not app_def:
            raise ListingNotFoundError(f"App definition {app_definition_id} not found.")

        # Check unique version tag
        existing_ver = db.query(AppVersion).filter(
            AppVersion.app_definition_id == app_definition_id,
            AppVersion.version_tag == version_tag,
        ).first()
        if existing_ver:
            raise InvalidManifestError(f"Version '{version_tag}' already exists for app '{app_def.app_key}'.")

        # Validate and prepare model dependencies
        resolved_deps: list[dict[str, Any]] = []
        for dep in model_dependencies or []:
            mv_id = dep.get("model_version_id")
            role = dep.get("dependency_role", "PRIMARY_GENERATOR")
            if not mv_id:
                continue

            mv = db.query(ModelVersion).filter(ModelVersion.id == mv_id).first()
            if not mv:
                raise UnapprovedReleaseError(f"Model version {mv_id} does not exist.")
            if mv.status == ModelVersionStatus.REVOKED:
                raise DependencyRevocationError(f"Cannot bind revoked model release {mv.version_tag}.")
            if mv.status != ModelVersionStatus.APPROVED:
                raise UnapprovedReleaseError(
                    f"Model release {mv.version_tag} is in {mv.status.value} state. Only APPROVED releases can be bound to App Zoo applications."
                )

            resolved_deps.append({
                "model_version": mv,
                "model_family_id": mv.family_id,
                "release_manifest_digest": mv.release_manifest_digest or "",
                "dependency_role": role,
            })

        # Construct canonical application manifest
        manifest_payload: dict[str, Any] = {
            "app_key": app_def.app_key,
            "version_tag": version_tag,
            "category": app_def.category,
            "license_id": license_id,
            "capabilities": sorted(capabilities or ["TEXT_GENERATION"]),
            "supported_input_types": sorted(supported_input_types or ["text/plain"]),
            "supported_output_types": sorted(supported_output_types or ["text/markdown"]),
            "supported_languages": sorted(supported_languages or ["en"]),
            "resources": {
                "min_ram_mb": min_ram_mb,
                "min_vram_mb": min_vram_mb,
                "target_hardware_key": target_hardware_key,
            },
            "model_dependencies": [
                {
                    "model_version_id": d["model_version"].id,
                    "release_manifest_digest": d["release_manifest_digest"],
                    "role": d["dependency_role"],
                }
                for d in resolved_deps
            ],
        }
        canonical_json = json.dumps(manifest_payload, sort_keys=True, separators=(",", ":"))
        manifest_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        app_ver = AppVersion(
            app_definition_id=app_def.id,
            version_tag=version_tag,
            description=description,
            app_manifest_json=canonical_json,
            manifest_digest=manifest_digest,
            capabilities_json=json.dumps(capabilities or ["TEXT_GENERATION"]),
            supported_input_types_json=json.dumps(supported_input_types or ["text/plain"]),
            supported_output_types_json=json.dumps(supported_output_types or ["text/markdown"]),
            supported_languages_json=json.dumps(supported_languages or ["en"]),
            license_id=license_id,
            min_ram_mb=min_ram_mb,
            min_vram_mb=min_vram_mb,
            target_hardware_key=target_hardware_key,
            status="ACTIVE",
            created_by=user_id,
        )
        db.add(app_ver)
        db.flush()

        # Add dependencies
        for d in resolved_deps:
            dep_rec = AppModelDependency(
                app_version_id=app_ver.id,
                model_family_id=d["model_family_id"],
                model_version_id=d["model_version"].id,
                release_manifest_digest=d["release_manifest_digest"],
                dependency_role=d["dependency_role"],
            )
            db.add(dep_rec)

        db.commit()
        db.refresh(app_ver)
        return app_ver

    @classmethod
    def create_app_listing(
        cls,
        db: Session,
        workspace_id: str,
        organization_id: str,
        user_id: str,
        app_version_id: str,
        title: str,
        description: str,
        slug: str | None = None,
        detailed_description: str | None = None,
        category: str = "DOCUMENT_ASSISTANT",
        tags: list[str] | None = None,
        visibility: CatalogVisibility = CatalogVisibility.WORKSPACE,
        distribution_status: DistributionStatus = DistributionStatus.METADATA_ONLY,
    ) -> AppListing:
        """Create a new App Zoo catalog listing."""
        app_ver = db.query(AppVersion).filter(AppVersion.id == app_version_id).first()
        if not app_ver:
            raise ListingNotFoundError(f"App version {app_version_id} not found.")

        app_def: AppDefinition = app_ver.app_definition

        base_slug = slug or _slugify(title)
        final_slug = base_slug
        counter = 1
        while db.query(AppListing).filter(AppListing.workspace_id == workspace_id, AppListing.slug == final_slug).first():
            final_slug = f"{base_slug}-{counter}"
            counter += 1

        listing = AppListing(
            organization_id=organization_id,
            workspace_id=workspace_id,
            app_definition_id=app_def.id,
            app_version_id=app_ver.id,
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

        # Hardware compatibility for app
        eval_badges = HardwareBadgeService.evaluate_model_compatibility(
            db=db,
            model_version_id=None,
            min_ram_mb=app_ver.min_ram_mb,
            min_vram_mb=app_ver.min_vram_mb,
            target_hardware_key=app_ver.target_hardware_key,
            artifact_digest=app_ver.manifest_digest,
        )
        HardwareBadgeService.sync_snapshots(
            db=db,
            listing_type="APP",
            listing_id=listing.id,
            model_version_id=None,
            eval_results=eval_badges,
            artifact_digest=app_ver.manifest_digest,
        )

        event = CatalogEvent(
            listing_type="APP",
            listing_id=listing.id,
            event_type="APP_LISTING_CREATED",
            triggered_by_user_id=user_id,
            message=f"App listing '{title}' created in DRAFT state.",
            metadata_json=json.dumps({"app_key": app_def.app_key, "version_tag": app_ver.version_tag}),
        )
        db.add(event)
        db.commit()
        db.refresh(listing)
        return listing

    @classmethod
    def submit_app_for_review(cls, db: Session, listing_id: str, user_id: str) -> AppListing:
        """Submit an app listing for catalog review."""
        listing = db.query(AppListing).filter(AppListing.id == listing_id).first()
        if not listing:
            raise ListingNotFoundError(f"App listing {listing_id} not found.")

        if listing.publication_status not in {PublicationStatus.DRAFT, PublicationStatus.REJECTED}:
            raise ListingReviewError(f"App listing cannot be submitted from {listing.publication_status.value} state.")

        listing.publication_status = PublicationStatus.SUBMITTED_FOR_REVIEW
        event = CatalogEvent(
            listing_type="APP",
            listing_id=listing.id,
            event_type="APP_LISTING_SUBMITTED",
            triggered_by_user_id=user_id,
            message="App listing submitted for publication review.",
            metadata_json="{}",
        )
        db.add(event)
        db.commit()
        db.refresh(listing)
        return listing

    @classmethod
    def review_and_publish_app(
        cls,
        db: Session,
        listing_id: str,
        reviewer_id: str,
        decision: str,  # APPROVED or REJECTED
        rationale: str,
    ) -> AppListing:
        """Review and publish (or reject) a submitted App Zoo listing."""
        listing = db.query(AppListing).filter(AppListing.id == listing_id).first()
        if not listing:
            raise ListingNotFoundError(f"App listing {listing_id} not found.")

        if listing.publication_status != PublicationStatus.SUBMITTED_FOR_REVIEW:
            raise ListingReviewError(f"Listing is in {listing.publication_status.value} and not pending review.")

        app_ver: AppVersion = listing.app_version
        if not app_ver:
            raise InvalidManifestError("App version is missing.")

        # Revalidate that ALL linked model versions are still APPROVED and not REVOKED
        for dep in app_ver.model_dependencies:
            mv: ModelVersion = dep.model_version
            if not mv or mv.status == ModelVersionStatus.REVOKED:
                raise DependencyRevocationError(
                    f"Cannot publish app: dependent model {mv.version_tag if mv else 'unknown'} has been REVOKED."
                )
            if mv.status != ModelVersionStatus.APPROVED:
                raise UnapprovedReleaseError(
                    f"Cannot publish app: dependent model {mv.version_tag} is in {mv.status.value} state."
                )

        review = CatalogReview(
            listing_type="APP",
            listing_id=listing.id,
            reviewer_id=reviewer_id,
            decision=decision,
            rationale=rationale,
            policy_snapshot_json=json.dumps({"visibility": listing.visibility.value}),
        )
        db.add(review)

        if decision == "APPROVED":
            eval_badges = HardwareBadgeService.evaluate_model_compatibility(
                db=db,
                model_version_id=None,
                min_ram_mb=app_ver.min_ram_mb,
                min_vram_mb=app_ver.min_vram_mb,
                target_hardware_key=app_ver.target_hardware_key,
                artifact_digest=app_ver.manifest_digest,
            )
            HardwareBadgeService.sync_snapshots(
                db=db,
                listing_type="APP",
                listing_id=listing.id,
                model_version_id=None,
                eval_results=eval_badges,
                artifact_digest=app_ver.manifest_digest,
            )

            sanitized_payload, pub_digest = PublicMetadataSanitizer.sanitize_app_listing(
                listing, app_ver, eval_badges
            )
            listing.public_metadata_snapshot_json = json.dumps(sanitized_payload)
            listing.publication_digest = pub_digest
            listing.publication_status = PublicationStatus.PUBLISHED
            listing.published_by = reviewer_id
            listing.published_at = datetime.now(UTC)

            event_msg = f"App listing published: {listing.title} ({listing.visibility.value})"
        else:
            listing.publication_status = PublicationStatus.REJECTED
            event_msg = f"App listing rejected by reviewer: {rationale}"

        event = CatalogEvent(
            listing_type="APP",
            listing_id=listing.id,
            event_type=f"APP_{decision}",
            triggered_by_user_id=reviewer_id,
            message=event_msg,
            metadata_json=json.dumps({"rationale": rationale}),
        )
        db.add(event)
        db.commit()
        db.refresh(listing)
        return listing

    @classmethod
    def search_and_list_apps(
        cls,
        db: Session,
        workspace_id: str | None = None,
        organization_id: str | None = None,
        query_text: str | None = None,
        category: str | None = None,
        visibility: CatalogVisibility | None = None,
        status: PublicationStatus | None = None,
        is_public_only: bool = False,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AppListing], int]:
        """Search and paginate App Zoo listings."""
        stmt = db.query(AppListing)

        if is_public_only:
            stmt = stmt.filter(
                AppListing.visibility == CatalogVisibility.PUBLIC,
                AppListing.publication_status == PublicationStatus.PUBLISHED,
            )
        else:
            filters = [AppListing.visibility == CatalogVisibility.PUBLIC]
            if organization_id:
                filters.append(
                    (AppListing.organization_id == organization_id)
                    & (AppListing.visibility == CatalogVisibility.ORGANIZATION)
                )
            if workspace_id:
                filters.append(AppListing.workspace_id == workspace_id)
            stmt = stmt.filter(or_(*filters))

            if status:
                stmt = stmt.filter(AppListing.publication_status == status)

        if visibility:
            stmt = stmt.filter(AppListing.visibility == visibility)
        if category:
            stmt = stmt.filter(AppListing.category == category)

        if query_text and query_text.strip():
            q = f"%{query_text.strip()}%"
            stmt = stmt.filter(
                or_(
                    AppListing.title.ilike(q),
                    AppListing.description.ilike(q),
                    AppListing.slug.ilike(q),
                    AppListing.tags_json.ilike(q),
                )
            )

        total_count = stmt.count()

        if sort_by == "title":
            order_col = AppListing.title.asc() if sort_dir == "asc" else AppListing.title.desc()
        else:
            order_col = AppListing.created_at.asc() if sort_dir == "asc" else AppListing.created_at.desc()

        items = stmt.order_by(order_col).offset((page - 1) * page_size).limit(min(page_size, 50)).all()
        return items, total_count

    @classmethod
    def get_app_listing_detail(cls, db: Session, listing_id: str) -> dict[str, Any]:
        """Retrieve full details of an App Zoo listing."""
        listing = db.query(AppListing).filter(AppListing.id == listing_id).first()
        if not listing:
            raise ListingNotFoundError(f"App listing {listing_id} not found.")

        app_ver: AppVersion = listing.app_version
        app_def: AppDefinition = listing.app_definition

        snapshots = (
            db.query(HardwareCompatibilitySnapshot)
            .filter(
                HardwareCompatibilitySnapshot.listing_type == "APP",
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

        snippets = InstallationGuideService.generate_app_snippets(listing, app_ver)

        deps = []
        for d in app_ver.model_dependencies:
            deps.append({
                "model_version_id": d.model_version_id,
                "model_family_slug": d.model_version.family.slug if d.model_version and d.model_version.family else "",
                "model_version_tag": d.model_version.version_tag if d.model_version else "",
                "release_manifest_digest": d.release_manifest_digest,
                "dependency_role": d.dependency_role,
                "model_status": d.model_version.status.value if d.model_version else "UNKNOWN",
            })

        all_app_versions = (
            db.query(AppVersion)
            .filter(AppVersion.app_definition_id == app_def.id)
            .order_by(AppVersion.created_at.desc())
            .all()
        )
        history = [
            {
                "version_tag": v.version_tag,
                "status": v.status,
                "manifest_digest": v.manifest_digest,
                "created_at": v.created_at.isoformat(),
                "is_current": v.id == app_ver.id,
            }
            for v in all_app_versions
        ]

        return {
            "listing": listing,
            "app_version": app_ver,
            "app_definition": app_def,
            "dependencies": deps,
            "hardware_badges": badge_list,
            "installation_snippets": snippets,
            "version_history": history,
        }
