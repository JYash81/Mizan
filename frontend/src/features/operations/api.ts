import { apiGet, apiPost, apiPut } from "../../lib/api/client";
import type {
  AlertInstance,
  AlertRule,
  AlertSilence,
  Incident,
  IncidentEvent,
  MetricsSummary,
  OperationalEvent,
  RollbackEligibilityResult,
  RollbackExecutionEvent,
  RollbackPolicy,
  ServiceLevelObjective,
  SiteSummary,
  SliSnapshot,
} from "./types";

export async function getMetricsSummary(siteId?: string): Promise<MetricsSummary> {
  const url = siteId ? `/ops/metrics/summary?site_id=${encodeURIComponent(siteId)}` : "/ops/metrics/summary";
  return apiGet<MetricsSummary>(url);
}

export async function listOperationalEvents(workspaceId?: string, limit = 50): Promise<OperationalEvent[]> {
  const q = new URLSearchParams();
  if (workspaceId) q.append("workspace_id", workspaceId);
  q.append("limit", limit.toString());
  return apiGet<OperationalEvent[]>(`/ops/events?${q.toString()}`);
}

export async function listAlertRules(workspaceId: string): Promise<AlertRule[]> {
  return apiGet<AlertRule[]>(`/ops/alerts/rules?workspace_id=${encodeURIComponent(workspaceId)}`);
}

export async function listAlertInstances(workspaceId?: string, status?: string): Promise<AlertInstance[]> {
  const q = new URLSearchParams();
  if (workspaceId) q.append("workspace_id", workspaceId);
  if (status) q.append("status", status);
  return apiGet<AlertInstance[]>(`/ops/alerts/instances?${q.toString()}`);
}

export async function acknowledgeAlert(instanceId: string, comment?: string): Promise<AlertInstance> {
  return apiPost<AlertInstance>(`/ops/alerts/instances/${instanceId}/acknowledge`, { comment });
}

export async function listAlertSilences(workspaceId: string): Promise<AlertSilence[]> {
  return apiGet<AlertSilence[]>(`/ops/alerts/silences?workspace_id=${encodeURIComponent(workspaceId)}`);
}

export async function createAlertSilence(
  workspaceId: string,
  payload: { rule_id?: string; starts_at: string; ends_at: string; reason: string }
): Promise<AlertSilence> {
  return apiPost<AlertSilence>(`/ops/alerts/silences?workspace_id=${encodeURIComponent(workspaceId)}`, payload);
}

export async function listSlos(workspaceId: string): Promise<ServiceLevelObjective[]> {
  return apiGet<ServiceLevelObjective[]>(`/ops/slos?workspace_id=${encodeURIComponent(workspaceId)}`);
}

export async function getSloSnapshot(sloId: string): Promise<SliSnapshot | null> {
  return apiGet<SliSnapshot | null>(`/ops/slos/${sloId}/snapshot`);
}

export async function recordSloSnapshot(sloId: string, totalEvents: number, goodEvents: number): Promise<SliSnapshot> {
  return apiPost<SliSnapshot>(
    `/ops/slos/${sloId}/snapshot?total_events=${totalEvents}&good_events=${goodEvents}`,
    {}
  );
}

export async function listIncidents(workspaceId: string, status?: string): Promise<Incident[]> {
  const q = new URLSearchParams();
  q.append("workspace_id", workspaceId);
  if (status) q.append("status", status);
  return apiGet<Incident[]>(`/ops/incidents?${q.toString()}`);
}

export async function getIncidentDetail(incidentId: string): Promise<Incident> {
  return apiGet<Incident>(`/ops/incidents/${incidentId}`);
}

export async function updateIncident(incidentId: string, payload: Partial<Incident>): Promise<Incident> {
  return apiPut<Incident>(`/ops/incidents/${incidentId}`, payload);
}

export async function addIncidentNote(incidentId: string, note: string): Promise<IncidentEvent> {
  return apiPost<IncidentEvent>(`/ops/incidents/${incidentId}/notes?note=${encodeURIComponent(note)}`, {});
}

export async function listRollbackPolicies(workspaceId: string): Promise<RollbackPolicy[]> {
  return apiGet<RollbackPolicy[]>(`/ops/rollback/policies?workspace_id=${encodeURIComponent(workspaceId)}`);
}

export async function updateRollbackPolicy(policyId: string, payload: Partial<RollbackPolicy>): Promise<RollbackPolicy> {
  return apiPut<RollbackPolicy>(`/ops/rollback/policies/${policyId}`, payload);
}

export async function checkRollbackEligibility(appId: string): Promise<RollbackEligibilityResult> {
  return apiGet<RollbackEligibilityResult>(`/ops/rollback/eligibility/${appId}`);
}

export async function triggerRollback(appId: string, reason: string): Promise<RollbackExecutionEvent> {
  return apiPost<RollbackExecutionEvent>("/ops/rollback/trigger", {
    runtime_application_id: appId,
    reason,
  });
}

export async function listRollbackHistory(appId?: string): Promise<RollbackExecutionEvent[]> {
  const url = appId ? `/ops/rollback/history?app_id=${encodeURIComponent(appId)}` : "/ops/rollback/history";
  return apiGet<RollbackExecutionEvent[]>(url);
}

export async function listSiteSummaries(workspaceId: string): Promise<SiteSummary[]> {
  return apiGet<SiteSummary[]>(`/ops/workspaces/${workspaceId}/site-summary`);
}
