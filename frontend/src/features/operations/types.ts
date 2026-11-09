/**
 * TypeScript definitions for Milestone 14: Operations Centre, Metrics,
 * Alerting, SLOs, Incidents, and Automated Rollback.
 */

export type AlertSeverity = "INFO" | "WARNING" | "CRITICAL";

export type AlertStatus =
  | "NORMAL"
  | "PENDING"
  | "FIRING"
  | "ACKNOWLEDGED"
  | "SILENCED"
  | "RESOLVED"
  | "SUPPRESSED";

export type RollbackMode = "DISABLED" | "MANUAL_ONLY" | "AUTOMATIC";

export type IncidentSeverity = "SEV1" | "SEV2" | "SEV3" | "SEV4";

export type IncidentStatus =
  | "OPEN"
  | "INVESTIGATING"
  | "MITIGATING"
  | "MONITORING"
  | "RESOLVED"
  | "CLOSED";

export interface MetricsSummary {
  site_id: string | null;
  active_slot: string;
  readiness_state: string;
  requests_total: number;
  error_rate_percentage: number;
  latency_p95_ms: number;
  latency_avg_ms: number;
  tokens_per_second: number;
  cpu_usage_percent: number;
  memory_allocated_mb: number;
  vram_allocated_mb: number;
  firing_alerts_count: number;
  slo_status: string;
  timestamp: string;
}

export interface AlertRule {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  metric_key: string;
  condition_operator: string;
  threshold: number;
  duration_seconds: number;
  consecutive_breaches: number;
  severity: AlertSeverity;
  is_enabled: boolean;
  cooldown_seconds: number;
  target_slot: string;
  created_at: string;
}

export interface AlertInstance {
  id: string;
  rule_id: string;
  customer_site_id: string | null;
  fingerprint: string;
  status: AlertStatus;
  current_value: number;
  breach_count: number;
  fired_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  labels: Record<string, string>;
  annotations: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AlertSilence {
  id: string;
  workspace_id: string;
  rule_id: string | null;
  customer_site_id: string | null;
  starts_at: string;
  ends_at: string;
  reason: string;
  created_by: string;
  created_at: string;
}

export interface ServiceLevelObjective {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  target_percentage: number;
  rolling_window_days: number;
  metric_key: string;
  good_events_definition: string;
  is_enabled: boolean;
  created_at: string;
}

export interface SliSnapshot {
  id: string;
  slo_id: string;
  customer_site_id: string | null;
  window_start: string;
  window_end: string;
  total_events: number;
  good_events: number;
  current_sli_percentage: number;
  error_budget_remaining_percentage: number;
  has_sufficient_data: boolean;
  burn_rate: number;
  created_at: string;
}

export interface RollbackPolicy {
  id: string;
  workspace_id: string;
  runtime_application_id: string | null;
  mode: RollbackMode;
  evaluation_window_seconds: number;
  error_rate_threshold_percentage: number;
  latency_p95_threshold_ms: number;
  cooldown_seconds: number;
  max_automatic_attempts_per_release: number;
  require_golden_test_pass: boolean;
  require_gate3_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RollbackExecutionEvent {
  id: string;
  runtime_application_id: string;
  from_slot_name: string;
  to_slot_name: string;
  from_model_version_id: string | null;
  to_model_version_id: string | null;
  trigger_type: string;
  trigger_reason: string;
  verification_passed: boolean;
  golden_test_run_id: string | null;
  status: string;
  error_detail: string | null;
  executed_by: string | null;
  created_at: string;
}

export interface IncidentEvent {
  id: string;
  incident_id: string;
  event_type: string;
  description: string;
  actor_id: string | null;
  created_at: string;
}

export interface Incident {
  id: string;
  workspace_id: string;
  customer_site_id: string | null;
  runtime_application_id: string | null;
  incident_number: number;
  title: string;
  description: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  primary_alert_id: string | null;
  assigned_to: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
  events: IncidentEvent[];
}

export interface OperationalEvent {
  id: string;
  customer_site_id: string | null;
  workspace_id: string | null;
  event_type: string;
  severity: string;
  source_component: string;
  summary: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface SiteSummary {
  id?: string;
  site_id: string;
  site_key: string;
  site_name: string;
  status: string;
  agent_enrolled: boolean;
  agent_alive: boolean;
  applications_count: number;
  firing_alerts_count: number;
  sync_consent: boolean;
}

export interface RollbackEligibilityResult {
  eligible: boolean;
  target_slot_id: string | null;
  target_slot_name: string | null;
  target_model_version_id: string | null;
  reasons: string[];
}
