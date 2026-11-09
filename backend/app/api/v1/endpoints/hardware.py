"""Hardware Knowledge Base and Resource Estimation API Endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.hardware import HardwareBenchmark, LocalHardwareSnapshot
from app.models.identity import User
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.hardware.benchmark_service import SafeBenchmarkService
from app.modules.hardware.compatibility_service import CompatibilityService
from app.modules.hardware.hardware_detection import inspect_local_hardware
from app.modules.hardware.profile_registry import HardwareProfileRepository
from app.modules.hardware.quantization_registry import QuantizationRegistry
from app.modules.hardware.resource_estimator import ResourceEstimatorService
from app.modules.hardware.schemas.hardware import (
    BenchmarkRunRequest,
    BenchmarkRunResponse,
    HardwareComparisonRequest,
    HardwareComparisonResponse,
    HardwareProfileCreate,
    HardwareProfileResponse,
    LocalHardwareSnapshotResponse,
    QuantizationFormatResponse,
    ResourceEstimateRequest,
    ResourceEstimateResponse,
)

router = APIRouter(tags=["Hardware Knowledge Base"])
repo = HardwareProfileRepository()
quant_registry = QuantizationRegistry()
resource_estimator = ResourceEstimatorService(profile_repo=repo, quant_registry=quant_registry)
comp_service = CompatibilityService(estimator=resource_estimator, profile_repo=repo)
benchmark_svc = SafeBenchmarkService()


@router.get(
    "/workspaces/{workspace_id}/hardware/profiles",
    response_model=list[HardwareProfileResponse],
)
def list_hardware_profiles(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    db: Session = Depends(get_db),
) -> list[HardwareProfileResponse]:
    """List available reference hardware profiles and custom profiles for workspace."""
    ws, _, _ = context
    profiles = repo.list_profiles(db, workspace_id=ws.id)
    results: list[HardwareProfileResponse] = []
    for p in profiles:
        resp = HardwareProfileResponse(
            id=p.id,
            profile_key=p.profile_key,
            name=p.name,
            category=p.category,
            evidence_type=p.evidence_type,
            description=p.description,
            cpu_manufacturer=p.cpu_manufacturer,
            cpu_model=p.cpu_model,
            physical_cores=p.physical_cores,
            logical_cores=p.logical_cores,
            cpu_frequency_mhz=p.cpu_frequency_mhz,
            system_ram_mb=p.system_ram_mb,
            available_ram_mb=p.available_ram_mb,
            gpu_vendor=p.gpu_vendor,
            gpu_model=p.gpu_model,
            gpu_vram_mb=p.gpu_vram_mb,
            memory_bandwidth_gbps=p.memory_bandwidth_gbps,
            supported_numeric_precisions=p.supported_numeric_precisions,
            supported_runtimes=p.supported_runtimes,
            supported_quantizations=p.supported_quantizations,
            supports_cpu_inference=p.supports_cpu_inference,
            supports_gpu_inference=p.supports_gpu_inference,
            supports_fine_tuning=p.supports_fine_tuning,
            source_url=p.source_url,
            reference_date=p.reference_date,
            verification_date=p.verification_date,
            limitations=p.limitations,
            is_reference=p.is_reference,
            organization_id=p.organization_id,
            workspace_id=p.workspace_id,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        results.append(resp)
    return results


@router.get(
    "/workspaces/{workspace_id}/hardware/profiles/{profile_key}",
    response_model=HardwareProfileResponse,
)
def get_hardware_profile(
    workspace_id: str,
    profile_key: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    db: Session = Depends(get_db),
) -> HardwareProfileResponse:
    """Retrieve detailed hardware profile specifications."""
    ws, _, _ = context
    p = repo.get_by_key(db, profile_key=profile_key, workspace_id=ws.id)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hardware profile '{profile_key}' not found.",
        )
    return HardwareProfileResponse(
        id=p.id,
        profile_key=p.profile_key,
        name=p.name,
        category=p.category,
        evidence_type=p.evidence_type,
        description=p.description,
        cpu_manufacturer=p.cpu_manufacturer,
        cpu_model=p.cpu_model,
        physical_cores=p.physical_cores,
        logical_cores=p.logical_cores,
        cpu_frequency_mhz=p.cpu_frequency_mhz,
        system_ram_mb=p.system_ram_mb,
        available_ram_mb=p.available_ram_mb,
        gpu_vendor=p.gpu_vendor,
        gpu_model=p.gpu_model,
        gpu_vram_mb=p.gpu_vram_mb,
        memory_bandwidth_gbps=p.memory_bandwidth_gbps,
        supported_numeric_precisions=p.supported_numeric_precisions,
        supported_runtimes=p.supported_runtimes,
        supported_quantizations=p.supported_quantizations,
        supports_cpu_inference=p.supports_cpu_inference,
        supports_gpu_inference=p.supports_gpu_inference,
        supports_fine_tuning=p.supports_fine_tuning,
        source_url=p.source_url,
        reference_date=p.reference_date,
        verification_date=p.verification_date,
        limitations=p.limitations,
        is_reference=p.is_reference,
        organization_id=p.organization_id,
        workspace_id=p.workspace_id,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.post(
    "/workspaces/{workspace_id}/hardware/profiles",
    response_model=HardwareProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_hardware_profile(
    workspace_id: str,
    payload: HardwareProfileCreate,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> HardwareProfileResponse:
    """Create a custom tenant-scoped hardware profile."""
    ws, org_mem, _ = context
    try:
        p = repo.create_custom_profile(
            db,
            data=payload,
            organization_id=org_mem.organization_id,
            workspace_id=ws.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return HardwareProfileResponse(
        id=p.id,
        profile_key=p.profile_key,
        name=p.name,
        category=p.category,
        evidence_type=p.evidence_type,
        description=p.description,
        cpu_manufacturer=p.cpu_manufacturer,
        cpu_model=p.cpu_model,
        physical_cores=p.physical_cores,
        logical_cores=p.logical_cores,
        cpu_frequency_mhz=p.cpu_frequency_mhz,
        system_ram_mb=p.system_ram_mb,
        available_ram_mb=p.available_ram_mb,
        gpu_vendor=p.gpu_vendor,
        gpu_model=p.gpu_model,
        gpu_vram_mb=p.gpu_vram_mb,
        memory_bandwidth_gbps=p.memory_bandwidth_gbps,
        supported_numeric_precisions=p.supported_numeric_precisions,
        supported_runtimes=p.supported_runtimes,
        supported_quantizations=p.supported_quantizations,
        supports_cpu_inference=p.supports_cpu_inference,
        supports_gpu_inference=p.supports_gpu_inference,
        supports_fine_tuning=p.supports_fine_tuning,
        source_url=p.source_url,
        reference_date=p.reference_date,
        verification_date=p.verification_date,
        limitations=p.limitations,
        is_reference=p.is_reference,
        organization_id=p.organization_id,
        workspace_id=p.workspace_id,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.post(
    "/workspaces/{workspace_id}/hardware/detect",
    response_model=LocalHardwareSnapshotResponse,
)
def detect_hardware_endpoint(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> LocalHardwareSnapshotResponse:
    """Safely inspect host CPU, memory, and GPU without external side effects."""
    ws, _, _ = context
    inspection = inspect_local_hardware()
    snapshot = repo.save_snapshot(
        db,
        workspace_id=ws.id,
        user_id=current_user.id,
        data=inspection,
    )
    return LocalHardwareSnapshotResponse(
        id=snapshot.id,
        workspace_id=snapshot.workspace_id,
        user_id=snapshot.user_id,
        cpu_model=snapshot.cpu_model,
        physical_cores=snapshot.physical_cores,
        logical_cores=snapshot.logical_cores,
        system_ram_mb=snapshot.system_ram_mb,
        available_ram_mb=snapshot.available_ram_mb,
        os_name=snapshot.os_name,
        os_release=snapshot.os_release,
        architecture=snapshot.architecture,
        has_nvidia_gpu=snapshot.has_nvidia_gpu,
        gpu_info=json.loads(snapshot.gpu_info_json) if snapshot.gpu_info_json else None,
        evidence_type=snapshot.evidence_type,
        detection_limitations=snapshot.detection_limitations,
        created_at=snapshot.created_at,
    )


@router.get(
    "/workspaces/{workspace_id}/hardware/snapshots/latest",
    response_model=LocalHardwareSnapshotResponse | None,
)
def get_latest_hardware_snapshot(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    db: Session = Depends(get_db),
) -> LocalHardwareSnapshotResponse | None:
    """Retrieve the latest detected hardware snapshot for workspace."""
    ws, _, _ = context
    snapshot = (
        db.execute(
            select(LocalHardwareSnapshot)
            .where(LocalHardwareSnapshot.workspace_id == ws.id)
            .order_by(LocalHardwareSnapshot.created_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if not snapshot:
        return None

    return LocalHardwareSnapshotResponse(
        id=snapshot.id,
        workspace_id=snapshot.workspace_id,
        user_id=snapshot.user_id,
        cpu_model=snapshot.cpu_model,
        physical_cores=snapshot.physical_cores,
        logical_cores=snapshot.logical_cores,
        system_ram_mb=snapshot.system_ram_mb,
        available_ram_mb=snapshot.available_ram_mb,
        os_name=snapshot.os_name,
        os_release=snapshot.os_release,
        architecture=snapshot.architecture,
        has_nvidia_gpu=snapshot.has_nvidia_gpu,
        gpu_info=json.loads(snapshot.gpu_info_json) if snapshot.gpu_info_json else None,
        evidence_type=snapshot.evidence_type,
        detection_limitations=snapshot.detection_limitations,
        created_at=snapshot.created_at,
    )


@router.post(
    "/workspaces/{workspace_id}/hardware/benchmark",
    response_model=BenchmarkRunResponse,
    dependencies=[Depends(require_csrf)],
)
def run_safe_cpu_benchmark(
    workspace_id: str,
    payload: BenchmarkRunRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BenchmarkRunResponse:
    """Run opt-in, bounded local CPU arithmetic benchmark with strict deadline."""
    ws, _, _ = context
    try:
        raw_result = benchmark_svc.run_cpu_benchmark(
            matrix_size=payload.matrix_size,
            iterations=payload.iterations,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {exc}",
        ) from exc

    saved = repo.save_benchmark(
        db,
        workspace_id=ws.id,
        user_id=current_user.id,
        data=raw_result,
    )
    return BenchmarkRunResponse(
        id=saved.id,
        workspace_id=saved.workspace_id,
        user_id=saved.user_id,
        snapshot_id=saved.snapshot_id,
        benchmark_name=saved.benchmark_name,
        benchmark_version=saved.benchmark_version,
        duration_ms=saved.duration_ms,
        operations_per_second=saved.operations_per_second,
        ram_before_mb=saved.ram_before_mb,
        ram_after_mb=saved.ram_after_mb,
        evidence_type=saved.evidence_type,
        status=saved.status,
        limitations=saved.limitations,
        started_at=saved.started_at,
        completed_at=saved.completed_at,
        created_at=saved.created_at,
    )


@router.get(
    "/workspaces/{workspace_id}/hardware/benchmarks/latest",
    response_model=BenchmarkRunResponse | None,
)
def get_latest_benchmark(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    db: Session = Depends(get_db),
) -> BenchmarkRunResponse | None:
    """Get the latest benchmark result for workspace."""
    ws, _, _ = context
    saved = (
        db.execute(
            select(HardwareBenchmark)
            .where(HardwareBenchmark.workspace_id == ws.id)
            .order_by(HardwareBenchmark.created_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if not saved:
        return None

    return BenchmarkRunResponse(
        id=saved.id,
        workspace_id=saved.workspace_id,
        user_id=saved.user_id,
        snapshot_id=saved.snapshot_id,
        benchmark_name=saved.benchmark_name,
        benchmark_version=saved.benchmark_version,
        duration_ms=saved.duration_ms,
        operations_per_second=saved.operations_per_second,
        ram_before_mb=saved.ram_before_mb,
        ram_after_mb=saved.ram_after_mb,
        evidence_type=saved.evidence_type,
        status=saved.status,
        limitations=saved.limitations,
        started_at=saved.started_at,
        completed_at=saved.completed_at,
        created_at=saved.created_at,
    )


@router.post(
    "/workspaces/{workspace_id}/hardware/estimate",
    response_model=ResourceEstimateResponse,
)
def estimate_workload_resources(
    workspace_id: str,
    payload: ResourceEstimateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ResourceEstimateResponse:
    """Calculate RAM/VRAM resource requirements and headroom for a model configuration."""
    ws, org_mem, _ = context
    try:
        est = resource_estimator.calculate_estimate(db, payload=payload, workspace_id=ws.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Persist estimate record
    est_dict = est.model_dump()
    rec = repo.save_resource_estimate(
        db,
        organization_id=org_mem.organization_id,
        workspace_id=ws.id,
        user_id=current_user.id,
        est=est_dict,
    )
    est.id = rec.id
    return est


@router.post(
    "/workspaces/{workspace_id}/hardware/compare",
    response_model=HardwareComparisonResponse,
)
def compare_hardware_compatibility(
    workspace_id: str,
    payload: HardwareComparisonRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    db: Session = Depends(get_db),
) -> HardwareComparisonResponse:
    """Compare model feasibility across all reference hardware profiles."""
    ws, _, _ = context
    try:
        return comp_service.compare_all_profiles(db, payload=payload, workspace_id=ws.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/workspaces/{workspace_id}/hardware/quantizations",
    response_model=list[QuantizationFormatResponse],
)
def list_quantization_formats(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_READ)
    ),
    db: Session = Depends(get_db),
) -> list[QuantizationFormatResponse]:
    """List supported quantization formats with nominal and effective bits."""
    formats = quant_registry.list_formats()
    results: list[QuantizationFormatResponse] = []
    for f in formats:
        results.append(
            QuantizationFormatResponse(
                id=f.format_key,
                format_key=f.format_key,
                format_family=f.format_family,
                nominal_bits=f.nominal_bits,
                effective_reference_bits=f.effective_reference_bits,
                runtime_requirements=f.runtime_requirements,
                supported_hardware=f.supported_hardware,
                calculation_assumptions=f.calculation_assumptions,
                limitations=f.limitations,
                source_reference=f.source_reference,
                registry_version=f.registry_version,
            )
        )
    return results
