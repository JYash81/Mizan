import { apiDelete, apiGet, apiPost, apiPut } from "../../lib/api/client";
import type {
  CandidateValidationRequest,
  CandidateValidationResult,
  CreateOptimizationProfileRequest,
  CreateRecommendationRunRequest,
  ObjectiveDefinition,
  OptimizationProfileResponse,
  RecommendationDecisionResponse,
  RecommendationRunListResponse,
  RecommendationRunResponse,
  RecordDecisionRequest,
  UpdateOptimizationProfileRequest,
} from "./types";

export async function fetchObjectives(workspaceId: string): Promise<ObjectiveDefinition[]> {
  return apiGet<ObjectiveDefinition[]>(`/workspaces/${workspaceId}/recommendations/objectives`);
}

export async function fetchPresets(
  workspaceId: string
): Promise<Record<string, Record<string, number>>> {
  return apiGet<Record<string, Record<string, number>>>(
    `/workspaces/${workspaceId}/recommendations/presets`
  );
}

export async function validateCandidates(
  workspaceId: string,
  req: CandidateValidationRequest
): Promise<CandidateValidationResult[]> {
  return apiPost<CandidateValidationResult[]>(
    `/workspaces/${workspaceId}/recommendations/validate-candidates`,
    req
  );
}

export async function createRecommendationRun(
  workspaceId: string,
  req: CreateRecommendationRunRequest
): Promise<RecommendationRunResponse> {
  return apiPost<RecommendationRunResponse>(
    `/workspaces/${workspaceId}/recommendations/runs`,
    req
  );
}

export async function fetchRecommendationRuns(
  workspaceId: string,
  skip = 0,
  limit = 50
): Promise<RecommendationRunListResponse> {
  return apiGet<RecommendationRunListResponse>(
    `/workspaces/${workspaceId}/recommendations/runs?skip=${skip}&limit=${limit}`
  );
}

export async function fetchRecommendationRun(
  workspaceId: string,
  runId: string
): Promise<RecommendationRunResponse> {
  return apiGet<RecommendationRunResponse>(
    `/workspaces/${workspaceId}/recommendations/runs/${runId}`
  );
}

export async function recordDecision(
  workspaceId: string,
  runId: string,
  req: RecordDecisionRequest
): Promise<RecommendationDecisionResponse> {
  return apiPost<RecommendationDecisionResponse>(
    `/workspaces/${workspaceId}/recommendations/runs/${runId}/decide`,
    req
  );
}

export async function archiveRecommendationRun(
  workspaceId: string,
  runId: string
): Promise<RecommendationRunResponse> {
  return apiPost<RecommendationRunResponse>(
    `/workspaces/${workspaceId}/recommendations/runs/${runId}/archive`,
    {}
  );
}

export async function exportRecommendationReport(
  workspaceId: string,
  runId: string,
  format: "json" | "markdown" | "csv"
): Promise<string> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
  const res = await fetch(
    `${baseUrl}/workspaces/${workspaceId}/recommendations/runs/${runId}/export?format=${format}`,
    { credentials: "include" }
  );
  if (!res.ok) {
    throw new Error(`Export failed with status ${res.status}`);
  }
  return res.text();
}

export async function fetchOptimizationProfiles(
  workspaceId: string
): Promise<OptimizationProfileResponse[]> {
  return apiGet<OptimizationProfileResponse[]>(
    `/workspaces/${workspaceId}/recommendations/profiles`
  );
}

export async function createOptimizationProfile(
  workspaceId: string,
  req: CreateOptimizationProfileRequest
): Promise<OptimizationProfileResponse> {
  return apiPost<OptimizationProfileResponse>(
    `/workspaces/${workspaceId}/recommendations/profiles`,
    req
  );
}

export async function updateOptimizationProfile(
  workspaceId: string,
  profileId: string,
  req: UpdateOptimizationProfileRequest
): Promise<OptimizationProfileResponse> {
  return apiPut<OptimizationProfileResponse>(
    `/workspaces/${workspaceId}/recommendations/profiles/${profileId}`,
    req
  );
}

export async function deleteOptimizationProfile(
  workspaceId: string,
  profileId: string
): Promise<void> {
  return apiDelete<void>(`/workspaces/${workspaceId}/recommendations/profiles/${profileId}`);
}

export interface WorkspaceExperimentSummary {
  id: string;
  name: string;
  status: string;
  target_model?: string;
  dataset_version_id?: string;
  evaluation_suite_version_id?: string;
  evaluation_split?: string;
  created_at: string;
}

export async function fetchWorkspaceExperiments(
  workspaceId: string
): Promise<{ items: WorkspaceExperimentSummary[]; total: number }> {
  return apiGet<{ items: WorkspaceExperimentSummary[]; total: number }>(
    `/workspaces/${workspaceId}/experiments?limit=100`
  );
}

export interface ExperimentTrialSummary {
  id: string;
  experiment_id: string;
  trial_number: number;
  name: string;
  status: string;
  configuration_digest: string;
  aggregate_score?: number | null;
  latency_p95_ms?: number | null;
  execution_duration_ms?: number | null;
}

export async function fetchExperimentDetail(
  workspaceId: string,
  experimentId: string
): Promise<{ id: string; name: string; trials: ExperimentTrialSummary[] }> {
  return apiGet<{ id: string; name: string; trials: ExperimentTrialSummary[] }>(
    `/workspaces/${workspaceId}/experiments/${experimentId}`
  );
}
