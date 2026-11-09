/**
 * TypeScript types for Milestone 13: Customer Runtime & Site Agent.
 */

export type SiteStatus = "ENROLLING" | "ACTIVE" | "OFFLINE" | "SUSPENDED" | "REVOKED";
export type AgentIdentityStatus = "ACTIVE" | "ROTATED" | "REVOKED";
export type RuntimeAppStatus = "INSTALLED" | "UPGRADING" | "ERROR" | "UNINSTALLED";
export type SlotName = "SLOT_A" | "SLOT_B";
export type SlotStatus = "EMPTY" | "STAGED" | "ACTIVE" | "FAILED" | "ARCHIVED";
export type ReadinessState = "UNINITIALIZED" | "LOADING" | "READY" | "UNHEALTHY";
export type GoldenTestOutcome = "NOT_RUN" | "PASSED" | "FAILED" | "BLOCKED" | "PARTIAL";

export interface CustomerSite {
  id: string;
  organization_id: string;
  workspace_id: string;
  site_key: string;
  site_name: string;
  description: string | null;
  status: SiteStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  agent_enrolled: boolean;
  active_runtime_version?: string | null;
  last_heartbeat_at?: string | null;
}

export interface EnrollmentTokenResponse {
  token_id: string;
  raw_token: string;
  expires_at: string;
  site_id: string;
  site_key: string;
}

export interface RuntimeApplication {
  id: string;
  customer_site_id: string;
  app_definition_id: string;
  app_version_id: string;
  app_manifest_digest: string;
  active_slot_name: SlotName;
  status: RuntimeAppStatus;
  installed_at: string;
  updated_at: string;
}

export interface RuntimeSlot {
  id: string;
  runtime_application_id: string;
  slot_name: SlotName;
  app_version_id: string | null;
  model_version_id: string | null;
  release_manifest_digest: string | null;
  status: SlotStatus;
  readiness_state: ReadinessState;
  golden_test_status: GoldenTestOutcome;
  last_golden_test_run_id: string | null;
  engine_adapter_key: string;
  configuration_snapshot: Record<string, unknown>;
  staged_at: string | null;
  activated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface GoldenTestCaseSummary {
  case_id: string;
  category: string;
  mandatory: boolean;
  passed: boolean;
  error_code: string | null;
}

export interface GoldenTestRun {
  id: string;
  runtime_slot_id: string;
  suite_id: string;
  suite_digest: string;
  runtime_version: string;
  outcome: GoldenTestOutcome;
  total_cases: int;
  passed_cases: int;
  failed_cases: int;
  duration_ms: number;
  results_summary: {
    cases: GoldenTestCaseSummary[];
  };
  started_at: string;
  completed_at: string | null;
}

type int = number;

export interface RuntimeActivationEvent {
  id: string;
  customer_site_id: string;
  runtime_application_id: string;
  previous_slot_name: string;
  new_slot_name: string;
  model_version_id: string;
  app_version_id: string;
  release_manifest_digest: string;
  golden_test_run_id: string | null;
  actor_id: string;
  switch_reason: string;
  created_at: string;
}

export interface RuntimeHealth {
  status: string;
  uptime_seconds: number;
  active_slot: string;
  readiness: string;
  engine: string;
  offline_mode: boolean;
  memory_allocated_mb: number;
}

export interface RuntimeChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface RuntimeChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    index: number;
    message: RuntimeChatMessage;
    finish_reason: string;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  offline_executed: boolean;
}

export interface RuntimeRagCitation {
  document_id: string;
  chunk_id: string;
  snippet: string;
  score: number;
}

export interface RuntimeRagQueryResponse {
  answer: string;
  citations: RuntimeRagCitation[];
  model_version_id: string;
  latency_ms: number;
  offline_executed: boolean;
}
