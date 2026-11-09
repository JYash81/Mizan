export type ExperimentStatus =
  | "DRAFT"
  | "VALIDATING"
  | "READY"
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "COMPLETED_WITH_ERRORS"
  | "FAILED"
  | "CANCEL_REQUESTED"
  | "CANCELLED";

export type TrialStatus =
  | "PENDING"
  | "VALIDATING"
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED"
  | "CANCEL_REQUESTED"
  | "CANCELLED";

export type SplitType = "VALIDATION" | "TEST";

export interface TrialConfig {
  chunk_size_chars: number;
  chunk_overlap_chars: number;
  top_k: number;
  retrieval_strategy?: string;
  embedding_provider?: string;
  embedding_model?: string;
  prompt_strategy?: string;
  provider_name: string;
  model_name: string;
  generation_params?: Record<string, unknown>;
}

export interface ExperimentTrial {
  id: string;
  organization_id: string;
  workspace_id: string;
  experiment_id: string;
  trial_number: number;
  name: string;
  status: TrialStatus;
  configuration_json: string;
  configuration_digest: string;
  evaluation_run_id: string | null;
  aggregate_score: number | null;
  score_breakdown: Record<string, number>;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  latency_p99_ms: number | null;
  execution_duration_ms: number | null;
  error_code: string | null;
  error_summary: string | null;
  retry_count: number;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Experiment {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: ExperimentStatus;
  dataset_id: string;
  dataset_version_id: string;
  gate1_approval_id: string | null;
  dataset_digest: string | null;
  evaluation_suite_id: string;
  evaluation_suite_version_id: string;
  canonical_suite_digest: string | null;
  evaluation_split: SplitType;
  baseline_config: Record<string, unknown>;
  configuration_digest: string | null;
  total_trials: number;
  completed_trials: number;
  failed_trials: number;
  cancelled_trials: number;
  started_at: string | null;
  completed_at: string | null;
  cancellation_requested_at: string | null;
  error_message: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  trials: ExperimentTrial[];
}

export interface ExperimentCreatePayload {
  name: string;
  slug?: string;
  description?: string;
  dataset_id: string;
  dataset_version_id: string;
  evaluation_suite_id: string;
  evaluation_suite_version_id: string;
  evaluation_split: SplitType;
  baseline_config: TrialConfig;
}

export interface MatrixGeneratePayload {
  strategy: "MANUAL" | "PARAMETRIC_VARIATION" | "PRESET_MATRIX";
  preset_name?: string;
  variations?: Record<string, unknown[]>;
  manual_trials?: TrialConfig[];
}

export interface TrialComparisonSummary {
  trial_id: string;
  trial_number: number;
  name: string;
  status: string;
  configuration: Record<string, unknown>;
  configuration_digest: string;
  evaluation_run_id: string | null;
  aggregate_score: number | null;
  metric_scores: Record<string, number | null>;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  latency_p99_ms: number | null;
  execution_duration_ms: number | null;
  error_summary: string | null;
}

export interface MetricObservation {
  metric_key: string;
  highest_observed_score: number | null;
  highest_scoring_trials: number[];
  lowest_observed_score: number | null;
  mean_observed_score: number | null;
}

export interface ExperimentComparisonResponse {
  experiment_id: string;
  experiment_name: string;
  status: string;
  dataset_version_id: string;
  evaluation_suite_version_id: string;
  evaluation_split: string;
  total_trials: number;
  completed_trials: number;
  failed_trials: number;
  trials: TrialComparisonSummary[];
  metric_keys: string[];
  metric_observations: MetricObservation[];
  lowest_observed_latency_ms: number | null;
  lowest_latency_trials: number[];
  compatibility_verified: boolean;
  compatibility_notes: string[];
}
