export type MaskingRunStatus = "PENDING" | "ANALYZING" | "MASKING" | "COMPLETED" | "FAILED" | "CANCELLED";

export type ExtractionCoverage =
  | "EXTRACTION_COMPLETE"
  | "PARTIALLY_EXTRACTED"
  | "OCR_REQUIRED"
  | "UNSUPPORTED_FORMAT"
  | "EXTRACTION_FAILED"
  | "EXCLUDED_BY_AUTHORIZED_REVIEWER";

export type FindingStatus = "DETECTED" | "CONFIRMED" | "FALSE_POSITIVE" | "MANUAL";

export type DecisionType =
  | "CONFIRMED"
  | "FALSE_POSITIVE"
  | "MANUALLY_ADDED"
  | "SPAN_CORRECTED"
  | "REPLACEMENT_CHANGED";

export type Gate1Decision = "APPROVED" | "REJECTED" | "INVALIDATED";

export type MaskingStrategy = "REPLACE_WITH_ENTITY_LABEL" | "REDACT" | "PARTIAL_MASK";

export interface MaskingProfile {
  id: string;
  organization_id: string;
  workspace_id: string | null;
  name: string;
  description: string | null;
  language: string;
  enabled_entities_json: string;
  replacement_strategy: MaskingStrategy;
  confidence_threshold: number;
  version: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface MaskingRun {
  id: string;
  workspace_id: string;
  dataset_id: string;
  dataset_version_id: string;
  source_dataset_digest: string;
  masking_profile_id: string | null;
  status: MaskingRunStatus;
  extraction_coverage: ExtractionCoverage;
  documents_processed: number;
  documents_failed: number;
  findings_count: number;
  unresolved_findings_count: number;
  masked_output_digest: string | null;
  error_message: string | null;
  created_by: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PiiFinding {
  id: string;
  masking_run_id: string;
  document_id: string;
  entity_type: string;
  recognizer_name: string;
  recognizer_version: string;
  detection_score: number;
  start_offset: number;
  end_offset: number;
  offset_unit: string;
  page_number: number | null;
  overlap_group_id: string | null;
  status: FindingStatus;
  is_manual: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaskingDecision {
  id: string;
  masking_run_id: string;
  finding_id: string;
  reviewer_user_id: string;
  decision_type: DecisionType;
  reason: string | null;
  custom_replacement: string | null;
  created_at: string;
}

export interface DocumentReview {
  document_id: string;
  document_name: string;
  file_type: string;
  original_text: string;
  masked_preview: string;
  findings: PiiFinding[];
  extraction_status: string;
  requires_ocr: boolean;
}

export interface Gate1Approval {
  id: string;
  organization_id: string;
  workspace_id: string;
  dataset_id: string;
  dataset_version_id: string;
  masking_run_id: string;
  source_dataset_digest: string;
  masked_output_digest: string;
  findings_digest: string;
  reviewer_user_id: string;
  reviewer_role_snapshot: string;
  decision: Gate1Decision;
  decision_reason: string | null;
  signature_algorithm: string;
  signing_key_id: string;
  approval_signature: string;
  canonical_payload: string;
  reviewed_at: string;
  created_at: string;
}

export interface Gate1Verification {
  approval_id: string;
  is_valid: boolean;
  decision: string;
  reviewer_user_id: string;
  reviewer_role: string;
  signature_algorithm: string;
  signing_key_id: string;
  source_dataset_digest: string;
  masked_output_digest: string;
  verification_message: string;
  verified_at: string;
}
