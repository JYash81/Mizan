export type QuestionCategory =
  | "FACTUAL"
  | "CONCEPTUAL"
  | "PROCEDURAL"
  | "COMPARISON"
  | "MULTI_HOP"
  | "NUMERICAL"
  | "DOCUMENT_SPECIFIC"
  | "UNANSWERABLE";

export type DifficultyLevel = "EASY" | "MEDIUM" | "HARD";

export type SplitType = "DEVELOPMENT" | "VALIDATION" | "HOLDOUT";

export type GroundTruthStatus =
  | "GENERATED"
  | "NEEDS_REVIEW"
  | "HUMAN_VERIFIED"
  | "REJECTED"
  | "ARCHIVED";

export type SuiteStatus = "DRAFT" | "READY" | "ARCHIVED";

export type RunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export type ScoringMethod =
  | "EXACT_MATCH"
  | "TOKEN_F1"
  | "KEYWORD_COVERAGE"
  | "RETRIEVAL_METRIC"
  | "CONTEXT_RELEVANCE"
  | "FAITHFULNESS"
  | "GROUNDEDNESS"
  | "CITATION_VERIFICATION"
  | "ABSTENTION"
  | "SAFETY"
  | "COMPLIANCE"
  | "WEIGHTED_SUM";

export interface EvaluationSuite {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description: string | null;
  domain: string | null;
  language: string;
  status: SuiteStatus;
  source_dataset_id: string | null;
  source_dataset_version_id: string | null;
  gate1_approval_id: string | null;
  case_count?: number;
  total_cases?: number;
  active_version?: number | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface EvaluationSuiteVersion {
  id: string;
  version_id?: string;
  suite_id: string;
  version_number: number;
  canonical_digest_sha256: string;
  case_count: number;
  rubric_id: string | null;
  rubric_version: number;
  created_by: string;
  created_at: string;
}

export interface EvaluationCase {
  id: string;
  organization_id: string;
  workspace_id: string;
  suite_id: string;
  suite_version_id: string | null;
  case_type: string;
  category: QuestionCategory;
  difficulty: DifficultyLevel;
  split: SplitType;
  language: string;
  question: string;
  expected_answer: string;
  is_unanswerable: boolean;
  source_document_ids: string[];
  source_chunk_ids: string[];
  ground_truth_status: GroundTruthStatus;
  generation_method: string;
  reviewer_notes: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface RubricCriterion {
  id: string;
  rubric_id: string;
  criterion_key: string;
  name: string;
  description: string;
  scoring_method: ScoringMethod;
  maximum_score: number;
  weight: number;
  minimum_acceptable_score: number;
  configuration: Record<string, unknown>;
  created_at: string;
}

export interface EvaluationRubric {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  domain: string | null;
  is_default: boolean;
  version: number;
  created_by: string;
  created_at: string;
  criteria: RubricCriterion[];
}

export interface EvaluationMetricResult {
  id: string;
  case_result_id: string;
  metric_key: string;
  raw_score: number;
  normalized_score: number;
  score_scale: string;
  status: string;
  evaluator_version: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface EvaluationCaseResult {
  id: string;
  run_id: string;
  case_id: string;
  actual_answer: string;
  actual_answer_digest: string;
  overall_case_score: number;
  status: string;
  retrieved_chunks: Array<Record<string, unknown>>;
  citations: Array<Record<string, unknown>>;
  latency_ms: number;
  created_at: string;
  metrics: EvaluationMetricResult[];
}

export interface EvaluationRun {
  id: string;
  organization_id: string;
  workspace_id: string;
  suite_id: string;
  suite_version_id: string;
  rubric_id: string | null;
  rubric_version: number;
  target_type: string;
  target_name: string;
  provider_name: string;
  model_name: string;
  status: RunStatus;
  total_cases: number;
  completed_cases: number;
  passed_cases: number;
  failed_cases: number;
  overall_score: number;
  score_breakdown: Record<string, number>;
  metric_summary?: Record<string, number>;
  error_message: string | null;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  execution_duration_ms: number;
  started_at: string | null;
  completed_at: string | null;
  created_by: string;
  created_at: string;
  case_results?: EvaluationCaseResult[];
}

export interface FullEvaluationReport {
  suite_name: string;
  run_id?: string;
  target_name: string;
  provider_name: string;
  model_name: string;
  execution_date: string;
  total_cases: number;
  completed_cases: number;
  overall_score: number;
  interpretation?: string;
  metric_summary: Record<string, number>;
  rubric_weights: Record<string, number>;
  latency_summary: {
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    total_duration_ms: number;
  };
  per_case_results: Array<{
    case_id: string;
    question: string;
    expected_answer: string;
    actual_answer: string;
    overall_case_score: number;
    status: string;
    latency_ms: number;
    metric_scores: Record<string, number>;
  }>;
}

export interface CreateSuitePayload {
  name: string;
  slug?: string;
  description?: string;
  domain?: string;
  language?: string;
  source_dataset_id?: string;
  source_dataset_version_id?: string;
  gate1_approval_id?: string;
}

export interface GenerateExamPayload {
  dataset_version_id?: string;
  language?: string;
  categories?: QuestionCategory[];
  questions_per_category?: number;
  target_splits?: {
    development?: number;
    validation?: number;
    holdout?: number;
  };
}

export interface FinalizeSuitePayload {
  rubric_id?: string;
  notes?: string;
}

export interface CreateManualCasePayload {
  question: string;
  expected_answer: string;
  category: QuestionCategory;
  difficulty: DifficultyLevel;
  split: SplitType;
  language?: string;
  is_unanswerable?: boolean;
  source_document_ids?: string[];
  source_chunk_ids?: string[];
  reviewer_notes?: string;
}

export interface ReviewCasePayload {
  decision: "APPROVED" | "REJECTED" | "EDITED" | "FLAGGED";
  comments?: string;
  reviewer_notes?: string;
  corrected_expected_answer?: string;
  updated_expected_answer?: string;
  corrected_category?: QuestionCategory;
  corrected_difficulty?: DifficultyLevel;
  corrected_split?: SplitType;
}

export interface CreateRunPayload {
  suite_id: string;
  suite_version_id?: string;
  rubric_id?: string;
  target_type: string;
  target_name: string;
  provider_name: string;
  model_name: string;
  retrieval_config?: Record<string, unknown>;
  supplied_responses?: Record<string, unknown>;
}
