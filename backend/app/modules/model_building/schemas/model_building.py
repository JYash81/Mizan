"""Pydantic schemas for Milestone 10: Model Building, Preflight, Artifacts & Evaluation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_key: str
    name: str
    description: str | None = None
    source_repository: str
    immutable_revision: str
    architecture: str
    parameter_count_millions: float
    context_length: int
    license_id: str
    license_status: str
    license_url: str | None = None
    commercial_use_allowed: bool | None = None
    is_gated: bool
    access_status: str
    requires_custom_code: bool
    estimated_download_bytes: int
    is_active: bool
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    verified_at: datetime | None = None
    created_at: datetime


class ModelValidateRequest(BaseModel):
    model_key: str
    raw_revision: str = "main"
    commercial_intended: bool = False
    hf_token: str | None = None
    user_confirmed_rights: bool = False


class ModelValidateResponse(BaseModel):
    model_key: str
    immutable_revision: str | None = None
    license_status: str
    access_status: str
    is_valid: bool
    warnings: list[str] = Field(default_factory=list)


class ModelBuildRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recipe_key: str
    recipe_version: str
    recipe_type: str
    name: str
    description: str
    supported_architectures: list[str] = Field(default_factory=list)
    supported_runtimes: list[str] = Field(default_factory=list)
    configuration_schema: dict[str, Any] = Field(default_factory=dict)
    default_config: dict[str, Any] = Field(default_factory=dict)
    dependency_lock: dict[str, str] = Field(default_factory=dict)
    resource_requirements: dict[str, Any] = Field(default_factory=dict)
    is_executable_locally: bool
    is_active: bool


class BuildPreflightRequest(BaseModel):
    model_id: str
    recipe_id: str
    execution_mode: str = "LOCAL_SMOKE_TEST"
    target_hardware_profile: str | None = None
    batch_size: int = 1
    context_length: int | None = None


class BuildPreflightResponse(BaseModel):
    model_key: str
    recipe_key: str
    execution_mode: str
    target_hardware_profile: str
    hardware_name: str
    weight_memory_mb: float
    kv_cache_mb: float
    peak_memory_mb: float
    download_size_mb: float
    total_disk_required_mb: float
    feasibility_status: str
    is_feasible: bool
    block_reasons: list[str] = Field(default_factory=list)
    evidence_type: str


class ExternalAuthorizationCreateRequest(BaseModel):
    dataset_id: str
    dataset_version_id: str
    purpose: str = "Model fine-tuning in Colab Free ephemeral runtime"
    valid_hours: int = 24


class ExternalAuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    dataset_id: str
    dataset_version_id: str
    dataset_version_digest: str
    purpose: str
    destination_class: str
    authorization_token: str
    is_revoked: bool
    expires_at: datetime
    created_at: datetime


class ModelBuildRunCreateRequest(BaseModel):
    name: str
    description: str | None = None
    source_model_id: str
    source_revision: str | None = None
    recipe_id: str
    execution_mode: str = "LOCAL_SMOKE_TEST"
    recommendation_run_id: str | None = None
    recommendation_candidate_id: str | None = None
    dataset_id: str | None = None
    dataset_version_id: str | None = None
    external_authorization_id: str | None = None
    target_hardware_profile: str | None = None
    training_config: dict[str, Any] = Field(default_factory=dict)


class ModelBuildCheckpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    build_run_id: str
    checkpoint_number: int
    step_number: int
    epoch: float
    storage_reference: str
    sha256: str
    configuration_digest: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ModelBuildEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    build_run_id: str
    actor_id: str | None = None
    event_type: str
    from_state: str | None = None
    to_state: str | None = None
    message: str
    metadata: dict[str, Any] | None = None
    created_at: datetime


class StagedArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    build_run_id: str
    artifact_type: str
    format: str
    storage_reference: str
    file_size_bytes: int
    sha256: str
    source_model_key: str
    source_model_revision: str
    quantization_type: str | None = None
    manifest_digest: str
    verification_status: str
    verification_details: dict[str, Any] = Field(default_factory=dict)
    is_staged_for_m11: bool
    created_at: datetime


class ModelEvaluationLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    build_run_id: str
    staged_artifact_id: str
    evaluation_run_id: str
    model_role: str
    evaluation_suite_id: str
    evaluation_split: str
    overall_score: float
    quality_delta: float
    latency_delta_ms: float | None = None
    memory_delta_mb: float | None = None
    comparison_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ModelBuildRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    created_by: str
    name: str
    description: str | None = None
    status: str
    execution_mode: str
    source_model_id: str
    source_revision: str
    recipe_id: str
    recipe_key: str
    recommendation_run_id: str | None = None
    recommendation_candidate_id: str | None = None
    dataset_id: str | None = None
    dataset_version_id: str | None = None
    gate1_approval_id: str | None = None
    manifest_digest: str
    training_config: dict[str, Any] = Field(default_factory=dict)
    build_manifest: dict[str, Any] = Field(default_factory=dict)
    preflight_snapshot: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error_summary: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    checkpoints: list[ModelBuildCheckpointResponse] = Field(default_factory=list)
    staged_artifacts: list[StagedArtifactResponse] = Field(default_factory=list)
    evaluation_links: list[ModelEvaluationLinkResponse] = Field(default_factory=list)


class ColabResultImportRequest(BaseModel):
    manifest_digest: str
    output_format: str = "SAFETENSORS"
    artifact_type: str = "LORA_ADAPTER"
    file_bytes_base64: str | None = None
    file_size_bytes: int
    sha256: str
    quantization_type: str | None = None
    execution_report: dict[str, Any] = Field(default_factory=dict)


class ColabResultImportResponse(BaseModel):
    build_run_id: str
    staged_artifact_id: str
    verification_status: str
    sha256: str
    message: str


class ModelEvaluationLinkRequest(BaseModel):
    staged_artifact_id: str
    evaluation_run_id: str
    model_role: str = "FINE_TUNED_MODEL"
    base_evaluation_score: float | None = None
