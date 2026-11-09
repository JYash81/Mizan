export type ExecutionMode = "LOCAL_SMOKE_TEST" | "MANUAL_COLAB_NOTEBOOK";

export type ModelBuildStatus =
  | "DRAFT"
  | "READY"
  | "RUNNING"
  | "CHECKPOINTED"
  | "COMPLETED"
  | "FAILED"
  | "BLOCKED_BY_RESOURCES"
  | "CANCELLED"
  | "ARCHIVED";

export type ArtifactType =
  | "LORA_ADAPTER"
  | "MERGED_MODEL"
  | "GGUF_QUANTIZED"
  | "AWQ_QUANTIZED"
  | "TOKENIZER"
  | "BUILD_MANIFEST";

export type ArtifactVerificationStatus =
  | "PENDING_VERIFICATION"
  | "VERIFIED"
  | "CHECKSUM_FAILED"
  | "FORMAT_INVALID"
  | "LEAKAGE_DETECTED";

export type ModelRole = "BASE_MODEL" | "FINE_TUNED_MODEL" | "QUANTIZED_MODEL";

export interface ModelSource {
  id: string;
  model_key: string;
  name: string;
  description?: string | null;
  source_repository: string;
  immutable_revision: string;
  architecture: string;
  parameter_count_millions: number;
  context_length: number;
  license_id: string;
  license_status: "APPROVED" | "COMMERCIAL_USE_ALLOWED" | "NON_COMMERCIAL_ONLY" | "RESTRICTED" | "NEEDS_REVIEW";
  license_url?: string | null;
  commercial_use_allowed?: boolean | null;
  is_gated: boolean;
  access_status: "OPEN" | "GATED_TOKEN_REQUIRED" | "AUTHENTICATED" | "RESTRICTED" | "UNKNOWN";
  requires_custom_code: boolean;
  estimated_download_bytes: number;
  is_active: boolean;
  source_metadata: Record<string, unknown>;
  verified_at?: string | null;
  created_at: string;
}

export interface ModelBuildRecipe {
  id: string;
  recipe_key: string;
  recipe_version: string;
  recipe_type: string;
  name: string;
  description: string;
  supported_architectures: string[];
  supported_runtimes: string[];
  configuration_schema: Record<string, unknown>;
  default_config: Record<string, unknown>;
  dependency_lock: Record<string, string>;
  resource_requirements: {
    min_ram_mb?: number;
    min_vram_mb?: number;
    min_disk_mb?: number;
    requires_gpu?: boolean;
    max_parameter_count_millions?: number;
  };
  is_executable_locally: boolean;
  is_active: boolean;
}

export interface BuildPreflightRequest {
  model_id: string;
  recipe_id: string;
  execution_mode: ExecutionMode;
  target_hardware_profile?: string | null;
  batch_size?: number;
  context_length?: number | null;
}

export interface BuildPreflightResponse {
  model_key: string;
  recipe_key: string;
  execution_mode: string;
  target_hardware_profile: string;
  hardware_name: string;
  weight_memory_mb: number;
  kv_cache_mb: number;
  peak_memory_mb: number;
  download_size_mb: number;
  total_disk_required_mb: number;
  feasibility_status: string;
  is_feasible: boolean;
  block_reasons: string[];
  evidence_type: string;
}

export interface ExternalAuthorization {
  id: string;
  workspace_id: string;
  dataset_id: string;
  dataset_version_id: string;
  dataset_version_digest: string;
  purpose: string;
  destination_class: string;
  authorization_token: string;
  is_revoked: boolean;
  expires_at: string;
  created_at: string;
}

export interface CreateExternalAuthorizationRequest {
  dataset_id: string;
  dataset_version_id: string;
  purpose?: string;
  valid_hours?: number;
}

export interface ModelBuildCheckpoint {
  id: string;
  build_run_id: string;
  checkpoint_number: number;
  step_number: number;
  epoch: number;
  storage_reference: string;
  sha256: string;
  configuration_digest: string;
  metrics: Record<string, unknown>;
  created_at: string;
}

export interface StagedArtifact {
  id: string;
  build_run_id: string;
  artifact_type: ArtifactType;
  format: string;
  storage_reference: string;
  file_size_bytes: number;
  sha256: string;
  source_model_key: string;
  source_model_revision: string;
  quantization_type?: string | null;
  manifest_digest: string;
  verification_status: ArtifactVerificationStatus;
  verification_details: Record<string, unknown>;
  is_staged_for_m11: boolean;
  created_at: string;
}

export interface ModelEvaluationLink {
  id: string;
  build_run_id: string;
  staged_artifact_id: string;
  evaluation_run_id: string;
  model_role: ModelRole;
  evaluation_suite_id: string;
  evaluation_split: string;
  overall_score: number;
  quality_delta: number;
  latency_delta_ms?: number | null;
  memory_delta_mb?: number | null;
  comparison_summary: {
    model_role?: string;
    evaluation_suite_id?: string;
    overall_score?: number;
    base_score?: number;
    quality_delta?: number;
    is_regression?: boolean;
    latency_p50_ms?: number | null;
  };
  created_at: string;
}

export interface ModelBuildEvent {
  id: string;
  build_run_id: string;
  actor_id?: string | null;
  event_type: string;
  from_state?: string | null;
  to_state?: string | null;
  message: string;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}

export interface ModelBuildRun {
  id: string;
  organization_id: string;
  workspace_id: string;
  created_by: string;
  name: string;
  description?: string | null;
  status: ModelBuildStatus;
  execution_mode: ExecutionMode;
  source_model_id: string;
  source_revision: string;
  recipe_id: string;
  recipe_key: string;
  recommendation_run_id?: string | null;
  recommendation_candidate_id?: string | null;
  dataset_id?: string | null;
  dataset_version_id?: string | null;
  gate1_approval_id?: string | null;
  manifest_digest: string;
  training_config: Record<string, unknown>;
  build_manifest: Record<string, unknown>;
  preflight_snapshot: Record<string, unknown>;
  warnings: string[];
  error_summary?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  checkpoints: ModelBuildCheckpoint[];
  staged_artifacts: StagedArtifact[];
  evaluation_links: ModelEvaluationLink[];
}

export interface CreateModelBuildRunRequest {
  name: string;
  description?: string | null;
  source_model_id: string;
  source_revision?: string | null;
  recipe_id: string;
  execution_mode: ExecutionMode;
  recommendation_run_id?: string | null;
  recommendation_candidate_id?: string | null;
  dataset_id?: string | null;
  dataset_version_id?: string | null;
  external_authorization_id?: string | null;
  target_hardware_profile?: string | null;
  training_config: Record<string, unknown>;
}

export interface ColabResultImportRequest {
  manifest_digest: string;
  output_format: string;
  artifact_type: ArtifactType;
  file_bytes_base64?: string | null;
  file_size_bytes: number;
  sha256: string;
  quantization_type?: string | null;
  execution_report: Record<string, unknown>;
}
