"""Package installation, cryptographic verification, and hardware preflight service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.artifact_registry import (
    Gate3Approval,
    Gate3Decision,
    ModelVersion,
    ModelVersionStatus,
)
from app.models.catalog import AppVersion
from app.models.runtime import (
    CustomerSite,
    ReadinessState,
    RuntimeApplication,
    RuntimeAppStatus,
    RuntimeSlot,
    SiteStatus,
    SlotName,
    SlotStatus,
)
from app.modules.masking.cryptography.signing_service import (
    SignatureVerificationError,
    verify_signature,
)
from app.modules.runtime.exceptions import (
    HardwarePreflightFailedError,
    PackageNotApprovedError,
    PackageVerificationError,
    SiteNotFoundError,
    SiteSuspendedOrRevokedError,
)

DISALLOWED_LICENSES = {"PROPRIETARY_RESTRICTED", "NO_DISTRIBUTION", "REVOKED"}


def verify_and_install_package(
    db: Session,
    customer_site_id: str,
    app_version_id: str,
    model_version_id: str,
) -> RuntimeApplication:
    """Perform preflight checks, Gate 3 attestation verification, and install package into customer site."""
    site = db.execute(
        select(CustomerSite).where(CustomerSite.id == customer_site_id)
    ).scalar_one_or_none()

    if not site:
        raise SiteNotFoundError(f"Customer site '{customer_site_id}' not found.")

    if site.status in (SiteStatus.REVOKED, SiteStatus.SUSPENDED):
        raise SiteSuspendedOrRevokedError(f"Customer site is '{site.status}'.")

    # 1. Verify Model Version & Gate 3 Approval
    model_version = db.execute(
        select(ModelVersion).where(ModelVersion.id == model_version_id)
    ).scalar_one_or_none()

    if not model_version:
        raise PackageVerificationError(f"Model version '{model_version_id}' does not exist.")

    if model_version.status != ModelVersionStatus.APPROVED:
        raise PackageNotApprovedError(
            f"Model version '{model_version_id}' has status '{model_version.status}', not APPROVED."
        )

    gate3 = db.execute(
        select(Gate3Approval).where(
            Gate3Approval.model_version_id == model_version_id,
            Gate3Approval.decision == Gate3Decision.APPROVED,
        )
    ).scalar_one_or_none()

    if not gate3:
        raise PackageNotApprovedError(
            f"No valid Gate 3 release approval found for model version '{model_version_id}'."
        )

    # Cryptographic signature verification
    try:
        verify_signature(
            canonical_payload=gate3.canonical_payload,
            signature_hex=gate3.approval_signature,
            key_id=gate3.signing_key_id,
        )
    except SignatureVerificationError as err:
        raise PackageVerificationError(
            f"Gate 3 Ed25519 signature verification failed: {err}"
        ) from err

    # 2. Verify Application Version & Manifest
    app_version = db.execute(
        select(AppVersion).where(AppVersion.id == app_version_id)
    ).scalar_one_or_none()

    if not app_version:
        raise PackageVerificationError(f"App version '{app_version_id}' does not exist.")

    if app_version.status not in ("ACTIVE", "APPROVED", "PUBLISHED"):
        raise PackageVerificationError(
            f"App version '{app_version_id}' has non-deployable status '{app_version.status}'."
        )

    # 3. License verification
    if app_version.license_id.upper() in DISALLOWED_LICENSES:
        raise PackageVerificationError(
            f"License '{app_version.license_id}' prohibits customer site distribution."
        )

    # 4. Hardware preflight check against Site Agent host platform info
    required_ram_mb = max(app_version.min_ram_mb, model_version.min_ram_mb)
    if site.agent_identity:
        platform = site.agent_identity.platform_info
        host_ram = platform.get("memory_mb") or platform.get("ram_mb")
        if host_ram is not None and float(host_ram) < required_ram_mb:
            raise HardwarePreflightFailedError(
                f"Customer site host memory ({host_ram} MB) is below package requirement ({required_ram_mb} MB)."
            )

    # 5. Look up or create RuntimeApplication
    runtime_app = db.execute(
        select(RuntimeApplication).where(
            RuntimeApplication.customer_site_id == site.id,
            RuntimeApplication.app_definition_id == app_version.app_definition_id,
        )
    ).scalar_one_or_none()

    if not runtime_app:
        runtime_app = RuntimeApplication(
            customer_site_id=site.id,
            app_definition_id=app_version.app_definition_id,
            app_version_id=app_version.id,
            app_manifest_digest=app_version.manifest_digest,
            active_slot_name=SlotName.SLOT_A.value,
            status=RuntimeAppStatus.INSTALLED,
        )
        db.add(runtime_app)
        db.flush()

        # Initialize Blue/Green deployment slots
        slot_a = RuntimeSlot(
            runtime_application_id=runtime_app.id,
            slot_name=SlotName.SLOT_A,
            app_version_id=app_version.id,
            model_version_id=model_version.id,
            release_manifest_digest=model_version.release_manifest_digest,
            status=SlotStatus.EMPTY,
            readiness_state=ReadinessState.UNINITIALIZED,
        )
        slot_b = RuntimeSlot(
            runtime_application_id=runtime_app.id,
            slot_name=SlotName.SLOT_B,
            status=SlotStatus.EMPTY,
            readiness_state=ReadinessState.UNINITIALIZED,
        )
        db.add_all([slot_a, slot_b])
    else:
        runtime_app.app_version_id = app_version.id
        runtime_app.app_manifest_digest = app_version.manifest_digest
        runtime_app.status = RuntimeAppStatus.INSTALLED

    db.commit()
    db.refresh(runtime_app)
    return runtime_app
