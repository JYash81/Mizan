export type ModelFamilyStatus = "ACTIVE" | "ARCHIVED";

export type ModelVersionStatus =
  | "DRAFT"
  | "PENDING_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "REVOKED"
  | "EXPIRED"
  | "ARCHIVED";

export type RegisteredArtifactType =
  | "BASE_WEIGHTS"
  | "LORA_ADAPTER"
  | "QLORA_ADAPTER"
  | "MERGED_WEIGHTS"
  | "GGUF_FP16"
  | "GGUF_Q8_0"
  | "GGUF_Q4_K_M"
  | "AWQ_QUANTIZED"
  | "TOKENIZER_PACKAGE"
  | "BUILD_REPORT"
  | "CONFIG"
  | "EVALUATION_REPORT"
  | "TRAINING_MANIFEST";

export type Gate3Decision = "APPROVED" | "REJECTED" | "REVOKED";

export interface RegisteredArtifact {
  id: string;
  artifact_type: RegisteredArtifactType;
  format: string;
  quantization_type?: string | null;
  file_size_bytes: number;
  sha256: string;
  storage_reference: string;
  is_verified: boolean;
  is_primary_weights: boolean;
  created_at: string;
}

export interface Gate3Approval {
  id: string;
  model_version_id: string;
  release_manifest_digest: string;
  decision: Gate3Decision;
  decision_reason?: string | null;
  reviewer_user_id: string;
  reviewer_role_snapshot: string;
  signature_algorithm: string;
  signature_purpose: string;
  signing_key_id: string;
  approval_signature: string;
  reviewed_at: string;
  expires_at?: string | null;
}

export interface Gate3Revocation {
  id: string;
  model_version_id: string;
  gate3_approval_id: string;
  revoked_by_user_id: string;
  revoked_by_role_snapshot: string;
  revocation_reason: string;
  revoked_at: string;
}

export interface ModelReleaseEvent {
  id: string;
  event_type: string;
  triggered_by_user_id: string;
  message: string;
  metadata_json: string;
  created_at: string;
}

export interface ModelVersion {
  id: string;
  family_id: string;
  version_tag: string;
  description?: string | null;
  status: ModelVersionStatus;
  source_model_key: string;
  source_model_revision: string;
  recipe_key: string;
  build_run_id?: string | null;
  dataset_id?: string | null;
  dataset_version_id?: string | null;
  dataset_version_digest?: string | null;
  gate1_approval_id?: string | null;
  base_evaluation_score?: number | null;
  final_evaluation_score?: number | null;
  quality_delta?: number | null;
  min_ram_mb: number;
  min_vram_mb: number;
  target_hardware_key?: string | null;
  release_manifest_digest?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  is_immutable: boolean;
  artifacts?: RegisteredArtifact[];
  gate3_approval?: Gate3Approval | null;
  revocations?: Gate3Revocation[];
  release_events?: ModelReleaseEvent[];
  release_manifest?: Record<string, unknown> | null;
  provenance_summary?: Record<string, unknown> | null;
}

export interface ModelFamily {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description?: string | null;
  task_type: string;
  status: ModelFamilyStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  versions?: ModelVersion[];
}

export interface CreateModelFamilyRequest {
  name: string;
  slug: string;
  description?: string;
  task_type?: string;
}

export interface CreateModelVersionRequest {
  version_tag: string;
  description?: string;
  build_run_id?: string;
  source_model_key?: string;
  source_model_revision?: string;
  recipe_key?: string;
  dataset_id?: string;
  dataset_version_id?: string;
  dataset_version_digest?: string;
  gate1_approval_id?: string;
  evaluation_run_id?: string;
  base_evaluation_score?: number;
  final_evaluation_score?: number;
  min_ram_mb?: number;
  min_vram_mb?: number;
  target_hardware_key?: string;
}

export interface RegisterStagedArtifactRequest {
  staged_artifact_id: string;
  is_primary_weights?: boolean;
}

export interface FinalizeManifestResponse {
  version_id: string;
  status: string;
  release_manifest_digest: string;
  artifact_count: number;
  provenance_summary: Record<string, unknown>;
}

export interface Gate3DecisionRequest {
  decision: "APPROVED" | "REJECTED";
  decision_reason?: string;
  enforce_separation_of_duties?: boolean;
  signing_key_id?: string;
}

export interface Gate3RevokeRequest {
  revocation_reason: string;
}

export interface Gate3SignatureVerifyResponse {
  is_valid: boolean;
  signing_key_id: string;
  signature_purpose: string;
  decision: string;
  reviewed_at: string;
  release_manifest_digest: string;
}
