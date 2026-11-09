export type OptimizationDirection = "MAXIMIZE" | "MINIMIZE" | "TARGET_RANGE";

export type MissingDataPolicy =
  | "PRESERVE_UNKNOWN"
  | "EXCLUDE_FROM_DOMINANCE"
  | "INELIGIBLE_IF_MANDATORY";

export type ObjectiveCategory =
  | "QUALITY"
  | "PERFORMANCE"
  | "RESOURCE"
  | "COST"
  | "SAFETY_COMPLIANCE";

export interface ObjectiveDefinition {
  key: string;
  display_name: string;
  category: ObjectiveCategory;
  direction: OptimizationDirection;
  unit: string;
  description: string;
  source_module: string;
  source_field: string;
  missing_data_policy: MissingDataPolicy;
  min_reasonable_value?: number | null;
  max_reasonable_value?: number | null;
  is_mandatory_by_default: boolean;
  version: string;
}

export type CandidateProvenanceStatus =
  | "VERIFIED"
  | "PARTIALLY_VERIFIED"
  | "INCOMPATIBLE"
  | "INCOMPLETE"
  | "EXCLUDED";

export type CandidateEligibilityStatus =
  | "ELIGIBLE"
  | "INELIGIBLE"
  | "NEEDS_REVIEW"
  | "INSUFFICIENT_EVIDENCE";

export type RecommendationRunStatus =
  | "DRAFT"
  | "VALIDATING"
  | "READY"
  | "RUNNING"
  | "COMPLETED"
  | "COMPLETED_WITH_WARNINGS"
  | "FAILED"
  | "ARCHIVED";

export type RecommendationDecisionType =
  | "ACCEPTED_FOR_FURTHER_REVIEW"
  | "REJECTED"
  | "DEFERRED"
  | "NEEDS_MORE_EVIDENCE";

export interface CandidateValidationRequest {
  experiment_ids: string[];
  trial_ids?: string[] | null;
}

export interface CandidateValidationResult {
  trial_id: string;
  experiment_id: string;
  trial_number: number;
  candidate_label: string;
  trial_status: string;
  configuration_digest: string;
  is_eligible: boolean;
  exclusion_reasons: string[];
  provenance_status: CandidateProvenanceStatus;
}

export interface ConstraintDetail {
  constraint_key: string;
  passed: boolean;
  threshold: unknown;
  actual_value: unknown;
  reason: string;
}

export interface RecommendationCandidateResponse {
  id: string;
  recommendation_run_id: string;
  experiment_id: string;
  experiment_trial_id: string;
  candidate_label: string;
  configuration_digest: string;
  evaluation_run_id?: string | null;
  dataset_id?: string | null;
  dataset_version_id?: string | null;
  evaluation_suite_id?: string | null;
  evaluation_suite_version_id?: string | null;
  evaluation_split?: string | null;
  hardware_profile_key?: string | null;
  provenance_status: CandidateProvenanceStatus;
  eligibility_status: CandidateEligibilityStatus;
  exclusion_reasons: string[];
  objective_values: Record<string, unknown>;
  normalized_objective_values: Record<string, number | null>;
  constraint_results: Record<string, ConstraintDetail>;
  pareto_frontier_member: boolean;
  dominated_by: string[];
  dominates: string[];
  weighted_score?: number | null;
  evidence_summary: Record<string, string>;
  explanation_text?: string | null;
  created_at: string;
}

export interface RecommendationDecisionResponse {
  id: string;
  recommendation_run_id: string;
  selected_candidate_id?: string | null;
  decision: RecommendationDecisionType;
  decision_reason: string;
  actor_id: string;
  created_at: string;
}

export interface RecommendationScenarioResponse {
  id: string;
  recommendation_run_id: string;
  scenario_name: string;
  weight_snapshot: Record<string, number>;
  ranking_snapshot: unknown;
  explanation?: string | null;
  created_at: string;
}

export interface RecommendationRunResponse {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  status: RecommendationRunStatus;
  algorithm_version: string;
  input_digest: string;
  result_digest?: string | null;
  total_candidates: number;
  eligible_candidates: number;
  frontier_candidates: number;
  error_summary?: string | null;
  created_by: string;
  created_at: string;
  completed_at?: string | null;
  candidates: RecommendationCandidateResponse[];
  decisions: RecommendationDecisionResponse[];
  scenarios: RecommendationScenarioResponse[];
}

export interface RecommendationRunSummaryResponse {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  status: RecommendationRunStatus;
  algorithm_version: string;
  input_digest: string;
  result_digest?: string | null;
  total_candidates: number;
  eligible_candidates: number;
  frontier_candidates: number;
  created_by: string;
  created_at: string;
  completed_at?: string | null;
}

export interface RecommendationRunListResponse {
  items: RecommendationRunSummaryResponse[];
  total: number;
}

export interface CreateRecommendationRunRequest {
  name: string;
  description?: string;
  experiment_ids: string[];
  trial_ids?: string[];
  optimization_profile_id?: string;
  selected_objectives?: string[];
  weights?: Record<string, number>;
  hard_constraints?: Record<string, unknown>;
}

export interface RecordDecisionRequest {
  selected_candidate_id?: string | null;
  decision: RecommendationDecisionType;
  decision_reason: string;
}

export interface OptimizationProfileResponse {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  objectives: string[];
  weights: Record<string, number>;
  constraints: Record<string, unknown>;
  preferred_hardware_profile?: string | null;
  budget_currency: string;
  version: number;
  created_by: string;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateOptimizationProfileRequest {
  name: string;
  description?: string;
  objectives?: string[];
  weights?: Record<string, number>;
  constraints?: Record<string, unknown>;
  preferred_hardware_profile?: string;
  budget_currency?: string;
}

export interface UpdateOptimizationProfileRequest {
  name?: string;
  description?: string;
  objectives?: string[];
  weights?: Record<string, number>;
  constraints?: Record<string, unknown>;
  preferred_hardware_profile?: string;
  budget_currency?: string;
}
