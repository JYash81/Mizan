"""Repository and registry operations for hardware profiles, snapshots, and benchmarks."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.hardware import (
    EvidenceType,
    HardwareBenchmark,
    HardwareProfile,
    LocalHardwareSnapshot,
    ResourceEstimateRecord,
)
from app.modules.hardware.schemas.hardware import HardwareProfileCreate


class HardwareProfileRepository:
    """Repository for hardware profiles, snapshots, and benchmark data."""

    def list_profiles(self, db: Session, workspace_id: str | None = None) -> list[HardwareProfile]:
        """List all reference profiles plus any custom profiles scoped to the workspace."""
        query = db.query(HardwareProfile).filter(
            (HardwareProfile.is_reference.is_(True))
            | (HardwareProfile.workspace_id == workspace_id)
        )
        return query.order_by(HardwareProfile.category, HardwareProfile.name).all()

    def get_by_key(
        self, db: Session, profile_key: str, workspace_id: str | None = None
    ) -> HardwareProfile | None:
        """Retrieve a hardware profile by key."""
        return (
            db.query(HardwareProfile)
            .filter(
                HardwareProfile.profile_key == profile_key,
                (HardwareProfile.is_reference.is_(True))
                | (HardwareProfile.workspace_id == workspace_id),
            )
            .first()
        )

    def create_custom_profile(
        self,
        db: Session,
        data: HardwareProfileCreate,
        organization_id: str,
        workspace_id: str,
    ) -> HardwareProfile:
        """Create a custom tenant-scoped hardware profile."""
        existing = (
            db.query(HardwareProfile)
            .filter(HardwareProfile.profile_key == data.profile_key)
            .first()
        )
        if existing:
            raise ValueError(f"Hardware profile key '{data.profile_key}' already exists.")

        prof = HardwareProfile(
            profile_key=data.profile_key,
            name=data.name,
            category=data.category,
            evidence_type=EvidenceType.USER_SUPPLIED,
            description=data.description,
            cpu_manufacturer=data.cpu_manufacturer,
            cpu_model=data.cpu_model,
            physical_cores=data.physical_cores,
            logical_cores=data.logical_cores,
            cpu_frequency_mhz=data.cpu_frequency_mhz,
            system_ram_mb=data.system_ram_mb,
            available_ram_mb=data.available_ram_mb,
            gpu_vendor=data.gpu_vendor,
            gpu_model=data.gpu_model,
            gpu_vram_mb=data.gpu_vram_mb,
            memory_bandwidth_gbps=data.memory_bandwidth_gbps,
            supported_numeric_precisions_json=json.dumps(data.supported_numeric_precisions),
            supported_runtimes_json=json.dumps(data.supported_runtimes),
            supported_quantizations_json=json.dumps(data.supported_quantizations),
            supports_cpu_inference=data.supports_cpu_inference,
            supports_gpu_inference=data.supports_gpu_inference,
            supports_fine_tuning=data.supports_fine_tuning,
            limitations=data.limitations,
            is_reference=False,
            organization_id=organization_id,
            workspace_id=workspace_id,
        )
        db.add(prof)
        db.commit()
        db.refresh(prof)
        return prof

    def save_snapshot(
        self, db: Session, workspace_id: str, user_id: str, data: dict[str, Any]
    ) -> LocalHardwareSnapshot:
        """Persist a local hardware inspection snapshot."""
        gpu_json = json.dumps(data.get("gpu_info")) if data.get("gpu_info") else None
        snap = LocalHardwareSnapshot(
            workspace_id=workspace_id,
            user_id=user_id,
            cpu_model=data["cpu_model"],
            physical_cores=data.get("physical_cores"),
            logical_cores=data.get("logical_cores"),
            system_ram_mb=data["system_ram_mb"],
            available_ram_mb=data["available_ram_mb"],
            os_name=data["os_name"],
            os_release=data["os_release"],
            architecture=data["architecture"],
            has_nvidia_gpu=data["has_nvidia_gpu"],
            gpu_info_json=gpu_json,
            evidence_type=data.get("evidence_type", EvidenceType.MEASURED),
            detection_limitations=data.get("detection_limitations"),
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)
        return snap

    def save_benchmark(
        self,
        db: Session,
        workspace_id: str,
        user_id: str,
        data: dict[str, Any],
        snapshot_id: str | None = None,
    ) -> HardwareBenchmark:
        """Persist a local hardware benchmark result."""
        bench = HardwareBenchmark(
            workspace_id=workspace_id,
            user_id=user_id,
            snapshot_id=snapshot_id,
            benchmark_name=data["benchmark_name"],
            benchmark_version=data["benchmark_version"],
            workload_params_json=data["workload_params_json"],
            duration_ms=data["duration_ms"],
            operations_per_second=data["operations_per_second"],
            ram_before_mb=data["ram_before_mb"],
            ram_after_mb=data["ram_after_mb"],
            evidence_type=data["evidence_type"],
            status=data["status"],
            limitations=data["limitations"],
            started_at=data["started_at"],
            completed_at=data["completed_at"],
        )
        db.add(bench)
        db.commit()
        db.refresh(bench)
        return bench

    def save_resource_estimate(
        self,
        db: Session,
        organization_id: str,
        workspace_id: str,
        user_id: str,
        est: dict[str, Any],
    ) -> ResourceEstimateRecord:
        """Persist a calculated resource estimate record."""
        rec = ResourceEstimateRecord(
            organization_id=organization_id,
            workspace_id=workspace_id,
            created_by=user_id,
            model_name=est["model_name"],
            parameter_count_millions=est["parameter_count_millions"],
            quantization_format=est["quantization_format"],
            context_length=est["context_length"],
            batch_size=est["batch_size"],
            execution_mode=est["execution_mode"],
            hardware_profile_key=est["hardware_profile_key"],
            weight_memory_mb=est["weight_memory_mb"],
            artifact_size_mb=est["artifact_size_mb"],
            kv_cache_memory_mb=est["kv_cache_memory_mb"],
            runtime_overhead_mb=est["runtime_overhead_mb"],
            peak_memory_mb=est["peak_memory_mb"],
            available_memory_mb=est["available_memory_mb"],
            headroom_mb=est["headroom_mb"],
            feasibility_status=est["feasibility_status"],
            evidence_type=est["evidence_type"],
            calculation_details_json=json.dumps(est.get("calculation_details", {})),
            assumptions_and_warnings_json=json.dumps(est.get("assumptions_and_warnings", [])),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec
