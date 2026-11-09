import { apiGet, apiPost, apiPatch } from "../../lib/api/client";
import type {
  Experiment,
  ExperimentCreatePayload,
  ExperimentTrial,
  MatrixGeneratePayload,
  ExperimentComparisonResponse,
} from "./types";

export async function fetchExperiments(
  workspaceId: string,
  statusFilter?: string
): Promise<Experiment[]> {
  const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
  return apiGet<Experiment[]>(`/workspaces/${workspaceId}/experiments${query}`);
}

export async function fetchExperiment(
  workspaceId: string,
  experimentId: string
): Promise<Experiment> {
  return apiGet<Experiment>(`/workspaces/${workspaceId}/experiments/${experimentId}`);
}

export async function createExperiment(
  workspaceId: string,
  payload: ExperimentCreatePayload
): Promise<Experiment> {
  return apiPost<Experiment>(`/workspaces/${workspaceId}/experiments`, payload);
}

export async function updateExperiment(
  workspaceId: string,
  experimentId: string,
  payload: { name?: string; description?: string }
): Promise<Experiment> {
  return apiPatch<Experiment>(`/workspaces/${workspaceId}/experiments/${experimentId}`, payload);
}

export async function generateMatrix(
  workspaceId: string,
  experimentId: string,
  payload: MatrixGeneratePayload
): Promise<Experiment> {
  return apiPost<Experiment>(
    `/workspaces/${workspaceId}/experiments/${experimentId}/matrix`,
    payload
  );
}

export async function validateMatrix(
  workspaceId: string,
  experimentId: string
): Promise<{ valid: boolean; total_trials: number; status: string; gate1_approved: boolean; digest_unique: boolean }> {
  return apiPost<{ valid: boolean; total_trials: number; status: string; gate1_approved: boolean; digest_unique: boolean }>(
    `/workspaces/${workspaceId}/experiments/${experimentId}/validate`
  );
}

export async function executeExperiment(
  workspaceId: string,
  experimentId: string
): Promise<Experiment> {
  return apiPost<Experiment>(
    `/workspaces/${workspaceId}/experiments/${experimentId}/execute`
  );
}

export async function cancelExperiment(
  workspaceId: string,
  experimentId: string
): Promise<Experiment> {
  return apiPost<Experiment>(
    `/workspaces/${workspaceId}/experiments/${experimentId}/cancel`
  );
}

export async function fetchComparison(
  workspaceId: string,
  experimentId: string
): Promise<ExperimentComparisonResponse> {
  return apiGet<ExperimentComparisonResponse>(
    `/workspaces/${workspaceId}/experiments/${experimentId}/comparison`
  );
}

export async function fetchTrial(
  workspaceId: string,
  experimentId: string,
  trialId: string
): Promise<ExperimentTrial> {
  return apiGet<ExperimentTrial>(
    `/workspaces/${workspaceId}/experiments/${experimentId}/trials/${trialId}`
  );
}

export async function exportReport(
  workspaceId: string,
  experimentId: string,
  format: "json" | "markdown" | "csv"
): Promise<string> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
  const res = await fetch(
    `${baseUrl}/workspaces/${workspaceId}/experiments/${experimentId}/export?format=${format}`,
    {
      credentials: "include",
    }
  );
  if (!res.ok) {
    throw new Error(`Export failed with status ${res.status}`);
  }
  return res.text();
}
