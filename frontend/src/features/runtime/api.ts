import { apiGet, apiPost } from "../../lib/api/client";
import type {
  CustomerSite,
  EnrollmentTokenResponse,
  GoldenTestRun,
  RuntimeActivationEvent,
  RuntimeApplication,
  RuntimeChatCompletionResponse,
  RuntimeHealth,
  RuntimeRagQueryResponse,
  RuntimeSlot,
  SlotName,
} from "./types";

// =========================================================================
// Customer Sites (Control Plane API)
// =========================================================================

export async function listCustomerSites(workspaceId: string): Promise<CustomerSite[]> {
  return apiGet<CustomerSite[]>(`/workspaces/${workspaceId}/sites`);
}

export async function createCustomerSite(
  workspaceId: string,
  payload: { site_key: string; site_name: string; description?: string }
): Promise<CustomerSite> {
  return apiPost<CustomerSite>(`/workspaces/${workspaceId}/sites`, payload);
}

export async function getCustomerSite(workspaceId: string, siteId: string): Promise<CustomerSite> {
  return apiGet<CustomerSite>(`/workspaces/${workspaceId}/sites/${siteId}`);
}

export async function generateEnrollmentToken(
  workspaceId: string,
  siteId: string
): Promise<EnrollmentTokenResponse> {
  return apiPost<EnrollmentTokenResponse>(`/workspaces/${workspaceId}/sites/${siteId}/enrollment-token`, {});
}

export async function revokeCustomerSite(
  workspaceId: string,
  siteId: string
): Promise<CustomerSite> {
  return apiPost<CustomerSite>(`/workspaces/${workspaceId}/sites/${siteId}/revoke`, {});
}

export async function listSiteApplications(
  workspaceId: string,
  siteId: string
): Promise<RuntimeApplication[]> {
  return apiGet<RuntimeApplication[]>(`/workspaces/${workspaceId}/sites/${siteId}/applications`);
}

export async function installPackageToSite(
  workspaceId: string,
  siteId: string,
  payload: { app_version_id: string; model_version_id: string }
): Promise<RuntimeApplication> {
  return apiPost<RuntimeApplication>(`/workspaces/${workspaceId}/sites/${siteId}/install-package`, payload);
}

// =========================================================================
// Customer Runtime & Blue/Green Slots API
// =========================================================================

export async function getRuntimeHealth(appId?: string): Promise<RuntimeHealth> {
  const qs = appId ? `?app_id=${encodeURIComponent(appId)}` : "";
  return apiGet<RuntimeHealth>(`/runtime/health${qs}`);
}

export async function getApplicationSlots(appId: string): Promise<RuntimeSlot[]> {
  return apiGet<RuntimeSlot[]>(`/runtime/applications/${appId}/slots`);
}

export async function stageCandidateSlot(
  appId: string,
  payload: {
    app_version_id: string;
    model_version_id: string;
    target_slot_name?: SlotName;
    engine_adapter_key?: string;
  }
): Promise<RuntimeSlot> {
  return apiPost<RuntimeSlot>(`/runtime/applications/${appId}/slots/stage`, payload);
}

export async function runGoldenTests(slotId: string, suiteId?: string): Promise<GoldenTestRun> {
  const qs = suiteId ? `?suite_id=${encodeURIComponent(suiteId)}` : "";
  return apiPost<GoldenTestRun>(`/runtime/slots/${slotId}/golden-tests/run${qs}`, {});
}

export async function activateSlot(
  appId: string,
  payload: { slot_name: SlotName; reason: string }
): Promise<RuntimeSlot> {
  return apiPost<RuntimeSlot>(`/runtime/applications/${appId}/slots/activate`, payload);
}

export async function rollbackSlot(
  appId: string,
  payload: { reason: string }
): Promise<RuntimeSlot> {
  return apiPost<RuntimeSlot>(`/runtime/applications/${appId}/slots/rollback`, payload);
}

export async function listActivationEvents(appId: string): Promise<RuntimeActivationEvent[]> {
  return apiGet<RuntimeActivationEvent[]>(`/runtime/applications/${appId}/activations`);
}

export async function executeChatCompletion(
  payload: { model: string; messages: Array<{ role: string; content: string }> },
  appId?: string
): Promise<RuntimeChatCompletionResponse> {
  const qs = appId ? `?app_id=${encodeURIComponent(appId)}` : "";
  return apiPost<RuntimeChatCompletionResponse>(`/runtime/v1/chat/completions${qs}`, payload);
}

export async function executeRagQuery(
  payload: { query: string; top_k?: number },
  appId?: string
): Promise<RuntimeRagQueryResponse> {
  const qs = appId ? `?app_id=${encodeURIComponent(appId)}` : "";
  return apiPost<RuntimeRagQueryResponse>(`/runtime/v1/rag/query${qs}`, payload);
}
