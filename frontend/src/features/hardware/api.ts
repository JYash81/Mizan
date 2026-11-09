import { apiGet, apiPost } from "../../lib/api/client";
import type {
  BenchmarkRun,
  CostEstimateResponse,
  FinancialAuthorizationResponse,
  Gate2ApprovalRequest,
  HardwareComparisonResponse,
  HardwareProfile,
  LocalHardwareSnapshot,
  PricingCatalogEntry,
  QuantizationFormat,
  ResourceEstimate,
  ResourceEstimateRequest,
} from "./types";

export async function fetchHardwareProfiles(workspaceId: string): Promise<HardwareProfile[]> {
  return apiGet<HardwareProfile[]>(`/workspaces/${workspaceId}/hardware/profiles`);
}

export async function fetchHardwareProfile(
  workspaceId: string,
  profileKey: string
): Promise<HardwareProfile> {
  return apiGet<HardwareProfile>(`/workspaces/${workspaceId}/hardware/profiles/${profileKey}`);
}

export async function detectHardware(workspaceId: string): Promise<LocalHardwareSnapshot> {
  return apiPost<LocalHardwareSnapshot>(`/workspaces/${workspaceId}/hardware/detect`, {});
}

export async function fetchLatestHardwareSnapshot(
  workspaceId: string
): Promise<LocalHardwareSnapshot | null> {
  return apiGet<LocalHardwareSnapshot | null>(`/workspaces/${workspaceId}/hardware/snapshots/latest`);
}

export async function runBenchmark(
  workspaceId: string,
  payload: { matrix_size?: number; iterations?: number } = {}
): Promise<BenchmarkRun> {
  return apiPost<BenchmarkRun>(`/workspaces/${workspaceId}/hardware/benchmark`, payload);
}

export async function fetchLatestBenchmark(workspaceId: string): Promise<BenchmarkRun | null> {
  return apiGet<BenchmarkRun | null>(`/workspaces/${workspaceId}/hardware/benchmarks/latest`);
}

export async function estimateResources(
  workspaceId: string,
  payload: ResourceEstimateRequest
): Promise<ResourceEstimate> {
  return apiPost<ResourceEstimate>(`/workspaces/${workspaceId}/hardware/estimate`, payload);
}

export async function compareHardware(
  workspaceId: string,
  payload: {
    model_name: string;
    parameter_count_millions: number;
    quantization_format: string;
    context_length: number;
    batch_size: number;
    execution_mode: string;
  }
): Promise<HardwareComparisonResponse> {
  return apiPost<HardwareComparisonResponse>(`/workspaces/${workspaceId}/hardware/compare`, payload);
}

export async function fetchQuantizations(workspaceId: string): Promise<QuantizationFormat[]> {
  return apiGet<QuantizationFormat[]>(`/workspaces/${workspaceId}/hardware/quantizations`);
}

export async function fetchPricingCatalog(workspaceId: string): Promise<PricingCatalogEntry[]> {
  return apiGet<PricingCatalogEntry[]>(`/workspaces/${workspaceId}/cost/pricing`);
}

export async function estimateCost(
  workspaceId: string,
  payload: {
    provider_name: string;
    instance_type: string;
    region: string;
    duration_hours: number;
    currency?: string;
  }
): Promise<CostEstimateResponse> {
  return apiPost<CostEstimateResponse>(`/workspaces/${workspaceId}/cost/estimate`, payload);
}

export async function fetchGate2Requests(
  workspaceId: string,
  statusFilter?: string
): Promise<Gate2ApprovalRequest[]> {
  const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
  return apiGet<Gate2ApprovalRequest[]>(`/workspaces/${workspaceId}/gate2/requests${query}`);
}

export async function fetchGate2Request(
  workspaceId: string,
  requestId: string
): Promise<Gate2ApprovalRequest> {
  return apiGet<Gate2ApprovalRequest>(`/workspaces/${workspaceId}/gate2/requests/${requestId}`);
}

export async function createGate2Request(
  workspaceId: string,
  payload: {
    title: string;
    purpose: string;
    workload_type: string;
    hardware_profile_key: string;
    provider_name: string;
    instance_type: string;
    region: string;
    estimated_duration_hours: number;
    max_duration_hours: number;
    max_authorized_budget: string;
    currency?: string;
  }
): Promise<Gate2ApprovalRequest> {
  return apiPost<Gate2ApprovalRequest>(`/workspaces/${workspaceId}/gate2/requests`, payload);
}

export async function decideGate2Request(
  workspaceId: string,
  requestId: string,
  payload: { decision: "APPROVE" | "REJECT"; decision_reason: string }
): Promise<Gate2ApprovalRequest> {
  return apiPost<Gate2ApprovalRequest>(
    `/workspaces/${workspaceId}/gate2/requests/${requestId}/decide`,
    payload
  );
}

export async function revokeGate2Request(
  workspaceId: string,
  requestId: string,
  payload: { revocation_reason: string }
): Promise<Gate2ApprovalRequest> {
  return apiPost<Gate2ApprovalRequest>(
    `/workspaces/${workspaceId}/gate2/requests/${requestId}/revoke`,
    payload
  );
}

export async function authorizeGate2(
  workspaceId: string,
  payload: { approval_request_id: string; proposed_cost?: string }
): Promise<FinancialAuthorizationResponse> {
  return apiPost<FinancialAuthorizationResponse>(`/workspaces/${workspaceId}/gate2/authorize`, payload);
}
