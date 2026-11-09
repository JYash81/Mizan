"""Pydantic schemas for Milestone 11 Artifact Registry and Gate 3 Approval APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelFamilyCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    task_type: str = "TEXT_GENERATION"


class RegisteredArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    artifact_type: str
    format: str
    quantization_type: str | None = None
    file_size_bytes: int
    sha256: str
    storage_reference: str
    is_verified: bool
    is_primary_weights: bool
    created_at: datetime


class ModelVersionCreateRequest(BaseModel):
    version_tag: str = Field(..., min_length=1, max_length=64)
    description: str | None = None
    build_run_id: str | None = None
    source_model_key: str | None = None
    source_model_revision: str | None = None
    recipe_key: str | None = None
    dataset_id: str | None = None
    dataset_version_id: str | None = None
    dataset_version_digest: str | None = None
    gate1_approval_id: str | None = None
    evaluation_run_id: str | None = None
    base_evaluation_score: float | None = None
    final_evaluation_score: float | None = None
    min_ram_mb: float = 0.0
    min_vram_mb: float = 0.0
    target_hardware_key: str | None = None


class Gate3ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_version_id: str
    release_manifest_digest: str
    decision: str
    decision_reason: str | None
    reviewer_user_id: str
    reviewer_role_snapshot: str
    signature_algorithm: str
    signature_purpose: str
    signing_key_id: str
    approval_signature: str
    reviewed_at: datetime
    expires_at: datetime | None = None


class Gate3RevocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_version_id: str
    gate3_approval_id: str
    revoked_by_user_id: str
    revoked_by_role_snapshot: str
    revocation_reason: str
    revoked_at: datetime


class ModelReleaseEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    triggered_by_user_id: str
    message: str
    metadata_json: str
    created_at: datetime


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    family_id: str
    version_tag: str
    description: str | None
    status: str
    source_model_key: str
    source_model_revision: str
    recipe_key: str
    build_run_id: str | None
    dataset_id: str | None
    dataset_version_id: str | None
    gate1_approval_id: str | None
    base_evaluation_score: float | None
    final_evaluation_score: float | None
    quality_delta: float | None
    min_ram_mb: float
    min_vram_mb: float
    target_hardware_key: str | None
    release_manifest_digest: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_immutable: bool


class ModelVersionDetailResponse(ModelVersionResponse):
    artifacts: list[RegisteredArtifactResponse] = []
    gate3_approval: Gate3ApprovalResponse | None = None
    revocations: list[Gate3RevocationResponse] = []
    release_events: list[ModelReleaseEventResponse] = []
    release_manifest: dict[str, Any] | None = None
    provenance_summary: dict[str, Any] | None = None


class ModelFamilyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    name: str
    slug: str
    description: str | None
    task_type: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    versions: list[ModelVersionResponse] = []


class RegisterStagedArtifactRequest(BaseModel):
    staged_artifact_id: str
    is_primary_weights: bool = False


class FinalizeManifestResponse(BaseModel):
    version_id: str
    status: str
    release_manifest_digest: str
    artifact_count: int
    provenance_summary: dict[str, Any]


class Gate3DecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    decision_reason: str | None = None
    enforce_separation_of_duties: bool = True
    signing_key_id: str | None = None


class Gate3RevokeRequest(BaseModel):
    revocation_reason: str = Field(..., min_length=5, max_length=1000)


class Gate3SignatureVerifyResponse(BaseModel):
    is_valid: bool
    signing_key_id: str
    signature_purpose: str
    decision: str
    reviewed_at: str
    release_manifest_digest: str
