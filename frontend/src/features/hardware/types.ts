/**
 * Type definitions for Milestone 8:
 * Hardware Knowledge Base, Resource Estimator, Cost Estimator & Gate 2 Financial Approval.
 */

export type EvidenceType =
  | "MEASURED"
  | "VENDOR_REFERENCE"
  | "ESTIMATED"
  | "SIMULATED"
  | "USER_SUPPLIED"
  | "UNVERIFIED";

export type HardwareProfileCategory =
  | "LOCAL_WORKSTATION"
  | "CLOUD_CPU"
  | "CLOUD_GPU"
  | "CUSTOM";

export type FeasibilityStatus =
  | "FEASIBLE_ESTIMATE"
  | "LIKELY_FEASIBLE"
  | "NOT_FEASIBLE"
  | "UNKNOWN"
  | "INSUFFICIENT_DATA";

export type PricingProvenance =
  | "OFFICIAL_SOURCE"
  | "USER_SUPPLIED"
  | "REFERENCE_ONLY"
  | "SYNTHETIC_TEST_DATA"
  | "UNVERIFIED";

export type Gate2ApprovalStatus =
  | "DRAFT"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "EXPIRED"
  | "REVOKED"
  | "INVALIDATED"
  | "BLOCKED_BY_POLICY";

export interface HardwareProfile {
  id: string;
  profile_key: string;
  name: string;
  category: HardwareProfileCategory;
  evidence_type: EvidenceType;
  description?: string;
  cpu_manufacturer?: string;
  cpu_model?: string;
  physical_cores?: number;
  logical_cores?: number;
  cpu_frequency_mhz?: number;
  system_ram_mb: number;
  available_ram_mb?: number;
  gpu_vendor?: string;
  gpu_model?: string;
  gpu_vram_mb?: number;
  memory_bandwidth_gbps?: number;
  supported_numeric_precisions: string[];
  supported_runtimes: string[];
  supported_quantizations: string[];
  supports_cpu_inference: boolean;
  supports_gpu_inference: boolean;
  supports_fine_tuning: boolean;
  source_url?: string;
  reference_date?: string;
  limitations?: string;
  is_reference: boolean;
  created_at: string;
  updated_at: string;
}

export interface LocalHardwareSnapshot {
  id: string;
  workspace_id: string;
  user_id: string;
  cpu_model: string;
  physical_cores?: number;
  logical_cores?: number;
  system_ram_mb: number;
  available_ram_mb: number;
  os_name: string;
  os_release: string;
  architecture: string;
  has_nvidia_gpu: boolean;
  gpu_info?: Record<string, unknown>;
  evidence_type: EvidenceType;
  detection_limitations?: string;
  created_at: string;
}

export interface BenchmarkRun {
  id: string;
  benchmark_name: string;
  duration_ms: number;
  operations_per_second: number;
  ram_before_mb: number;
  ram_after_mb: number;
  evidence_type: EvidenceType;
  status: string;
  limitations: string;
  started_at: string;
  completed_at: string;
  created_at: string;
}

export interface QuantizationFormat {
  id: string;
  format_key: string;
  format_family: string;
  nominal_bits: number;
  effective_reference_bits: number;
  runtime_requirements: string[];
  supported_hardware: string[];
  calculation_assumptions: string;
  limitations: string;
  source_reference: string;
  registry_version: string;
}

export interface ResourceEstimateRequest {
  model_name: string;
  parameter_count_millions: number;
  quantization_format: string;
  context_length: number;
  batch_size: number;
  execution_mode: string;
  hardware_profile_key: string;
  num_layers?: number;
  num_kv_heads?: number;
  head_dim?: number;
  hidden_size?: number;
}

export interface ResourceEstimate {
  id?: string;
  model_name: string;
  parameter_count_millions: number;
  quantization_format: string;
  context_length: number;
  batch_size: number;
  execution_mode: string;
  hardware_profile_key: string;
  hardware_profile_name: string;
  weight_memory_mb: number;
  artifact_size_mb: number;
  kv_cache_memory_mb: number;
  runtime_overhead_mb: number;
  peak_memory_mb: number;
  available_memory_mb: number;
  headroom_mb: number;
  feasibility_status: FeasibilityStatus;
  evidence_type: EvidenceType;
  calculation_details: {
    effective_bits_per_weight?: number;
    safety_margin_factor?: number;
    required_with_safety_margin_mb?: number;
    kv_cache_calculation_method?: string;
    nominal_format_family?: string;
  };
  assumptions_and_warnings: string[];
}

export interface HardwareComparisonItem {
  profile_key: string;
  profile_name: string;
  category: string;
  evidence_type: EvidenceType;
  required_ram_mb: number;
  required_vram_mb: number;
  available_ram_mb: number;
  available_vram_mb: number;
  headroom_mb: number;
  feasibility_status: FeasibilityStatus;
  runtime_supported: boolean;
  quantization_supported: boolean;
  limitations?: string;
  reason: string;
}

export interface HardwareComparisonResponse {
  model_name: string;
  parameter_count_millions: number;
  quantization_format: string;
  context_length: number;
  batch_size: number;
  execution_mode: string;
  profiles: HardwareComparisonItem[];
}

export interface PricingCatalogEntry {
  id: string;
  provider_name: string;
  resource_type: string;
  instance_type: string;
  region: string;
  currency: string;
  hourly_rate: string;
  storage_monthly_rate_per_gb?: string;
  billing_unit_seconds: number;
  provenance: PricingProvenance;
  effective_from: string;
  is_verified: boolean;
  catalog_version: string;
}

export interface CostBreakdownItem {
  component_name: string;
  quantity: number;
  unit: string;
  rate: string;
  subtotal: string;
  notes?: string;
}

export interface CostEstimateResponse {
  total_estimated_cost: string;
  currency: string;
  status: string;
  provider_name: string;
  instance_type: string;
  region: string;
  duration_hours: number;
  duration_source: string;
  billable_hours: number;
  billing_unit_seconds: number;
  pricing_catalog_version: string;
  pricing_provenance?: PricingProvenance;
  price_is_verified: boolean;
  cost_breakdown: CostBreakdownItem[];
  warnings: string[];
}

export interface Gate2ApprovalEvent {
  id: string;
  approval_request_id: string;
  actor_id: string;
  event_type: string;
  previous_status?: string;
  new_status: string;
  message?: string;
  metadata_json?: string;
  created_at: string;
}

export interface Gate2ApprovalRequest {
  id: string;
  organization_id: string;
  workspace_id: string;
  requester_id: string;
  title: string;
  purpose: string;
  workload_type: string;
  hardware_profile_key: string;
  provider_name: string;
  instance_type: string;
  region: string;
  estimated_duration_hours: number;
  max_duration_hours: number;
  estimated_compute_cost: string;
  estimated_storage_cost: string;
  estimated_total_cost: string;
  max_authorized_budget: string;
  currency: string;
  proposal_digest: string;
  proposal_payload_json: string;
  pricing_snapshot_json: string;
  pricing_catalog_version: string;
  status: Gate2ApprovalStatus;
  approver_id?: string;
  approver_role_snapshot?: string;
  approval_signature?: string;
  signing_key_id?: string;
  signed_payload?: string;
  signed_at?: string;
  decision_reason?: string;
  rejection_reason?: string;
  revocation_reason?: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
  events: Gate2ApprovalEvent[];
}

export interface FinancialAuthorizationResponse {
  authorized: boolean;
  status: Gate2ApprovalStatus;
  reason: string;
  proposal_digest_match: boolean;
  signature_valid: boolean;
  policy_allowed: boolean;
  max_authorized_budget?: string;
  estimated_total_cost?: string;
  expires_at?: string;
  details?: Record<string, unknown>;
}
