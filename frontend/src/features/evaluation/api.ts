import { apiGet, apiPost, buildApiUrl, getSessionToken } from "../../lib/api/client";
import type {
  CreateManualCasePayload,
  CreateRunPayload,
  CreateSuitePayload,
  EvaluationCase,
  EvaluationCaseResult,
  EvaluationRubric,
  EvaluationRun,
  EvaluationSuite,
  EvaluationSuiteVersion,
  FinalizeSuitePayload,
  FullEvaluationReport,
  GenerateExamPayload,
  ReviewCasePayload,
} from "./types";

export async function fetchSuites(workspaceId: string): Promise<EvaluationSuite[]> {
  return apiGet<EvaluationSuite[]>(`/workspaces/${workspaceId}/evaluation/suites`);
}

export async function fetchSuite(
  workspaceId: string,
  suiteId: string
): Promise<EvaluationSuite> {
  return apiGet<EvaluationSuite>(`/workspaces/${workspaceId}/evaluation/suites/${suiteId}`);
}

export async function createSuite(
  workspaceId: string,
  payload: CreateSuitePayload
): Promise<EvaluationSuite> {
  return apiPost<EvaluationSuite>(`/workspaces/${workspaceId}/evaluation/suites`, payload);
}

export async function generateExam(
  workspaceId: string,
  suiteId: string,
  payload: GenerateExamPayload
): Promise<{ generated_count: number; cases: EvaluationCase[] }> {
  return apiPost<{ generated_count: number; cases: EvaluationCase[] }>(
    `/workspaces/${workspaceId}/evaluation/suites/${suiteId}/generate-cases`,
    payload
  );
}

export async function finalizeSuite(
  workspaceId: string,
  suiteId: string,
  payload?: FinalizeSuitePayload
): Promise<EvaluationSuiteVersion> {
  return apiPost<EvaluationSuiteVersion>(
    `/workspaces/${workspaceId}/evaluation/suites/${suiteId}/finalize`,
    payload ?? {}
  );
}

export async function fetchSuiteVersions(
  workspaceId: string,
  suiteId: string
): Promise<EvaluationSuiteVersion[]> {
  return apiGet<EvaluationSuiteVersion[]>(
    `/workspaces/${workspaceId}/evaluation/suites/${suiteId}/versions`
  );
}

export async function fetchCases(
  workspaceId: string,
  suiteId: string,
  params?: { split?: string; ground_truth_status?: string }
): Promise<EvaluationCase[]> {
  const query = new URLSearchParams();
  if (params?.split) query.set("split", params.split);
  if (params?.ground_truth_status) query.set("ground_truth_status", params.ground_truth_status);
  const qStr = query.toString() ? `?${query.toString()}` : "";
  return apiGet<EvaluationCase[]>(
    `/workspaces/${workspaceId}/evaluation/suites/${suiteId}/cases${qStr}`
  );
}

export async function createManualCase(
  workspaceId: string,
  suiteId: string,
  payload: CreateManualCasePayload
): Promise<EvaluationCase> {
  return apiPost<EvaluationCase>(
    `/workspaces/${workspaceId}/evaluation/suites/${suiteId}/manual-cases`,
    payload
  );
}

export async function reviewCase(
  workspaceId: string,
  caseId: string,
  payload: ReviewCasePayload,
  suiteId?: string
): Promise<EvaluationCase> {
  const path = suiteId
    ? `/workspaces/${workspaceId}/evaluation/suites/${suiteId}/cases/${caseId}/review`
    : `/workspaces/${workspaceId}/evaluation/cases/${caseId}/review`;
  return apiPost<EvaluationCase>(path, payload);
}

export async function fetchRubrics(workspaceId: string): Promise<EvaluationRubric[]> {
  return apiGet<EvaluationRubric[]>(`/workspaces/${workspaceId}/evaluation/rubrics`);
}

export async function fetchDefaultRubric(
  workspaceId: string
): Promise<EvaluationRubric> {
  return apiGet<EvaluationRubric>(`/workspaces/${workspaceId}/evaluation/rubrics/default`);
}

export async function createRubric(
  workspaceId: string,
  payload: Partial<EvaluationRubric>
): Promise<EvaluationRubric> {
  return apiPost<EvaluationRubric>(`/workspaces/${workspaceId}/evaluation/rubrics`, payload);
}

export async function createAndExecuteRun(
  workspaceId: string,
  payload: CreateRunPayload
): Promise<EvaluationRun> {
  return apiPost<EvaluationRun>(`/workspaces/${workspaceId}/evaluation/runs`, payload);
}

export async function fetchRuns(
  workspaceId: string,
  suiteId?: string
): Promise<EvaluationRun[]> {
  const path = suiteId
    ? `/workspaces/${workspaceId}/evaluation/runs?suite_id=${suiteId}`
    : `/workspaces/${workspaceId}/evaluation/runs`;
  return apiGet<EvaluationRun[]>(path);
}

export async function fetchRun(
  workspaceId: string,
  runId: string
): Promise<EvaluationRun> {
  return apiGet<EvaluationRun>(`/workspaces/${workspaceId}/evaluation/runs/${runId}`);
}

export async function fetchRunResults(
  workspaceId: string,
  runId: string
): Promise<EvaluationCaseResult[]> {
  return apiGet<EvaluationCaseResult[]>(
    `/workspaces/${workspaceId}/evaluation/runs/${runId}/results`
  );
}

export async function fetchReport(
  workspaceId: string,
  runId: string,
  format: "json" | "markdown" | "csv" = "json"
): Promise<FullEvaluationReport | string> {
  const url = buildApiUrl(`/workspaces/${workspaceId}/evaluation/runs/${runId}/report?format=${format}`);
  const headers = new Headers({
    Accept: format === "json" ? "application/json" : "text/plain",
  });
  const token = getSessionToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(url, {
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch report in ${format} format`);
  }
  if (format === "json") {
    return (await response.json()) as FullEvaluationReport;
  }
  return await response.text();
}
