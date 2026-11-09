import { apiGet, apiPost } from "../../lib/api/client";
import type {
  BuildPreflightRequest,
  BuildPreflightResponse,
  ColabResultImportRequest,
  CreateExternalAuthorizationRequest,
  CreateModelBuildRunRequest,
  ExternalAuthorization,
  ModelBuildRecipe,
  ModelBuildRun,
  ModelEvaluationLink,
  ModelSource,
  StagedArtifact,
} from "./types";

export async function fetchModelSources(workspaceId: string): Promise<ModelSource[]> {
  return apiGet<ModelSource[]>(`/workspaces/${workspaceId}/model-building/models`);
}

export async function fetchModelSource(workspaceId: string, modelId: string): Promise<ModelSource> {
  return apiGet<ModelSource>(`/workspaces/${workspaceId}/model-building/models/${modelId}`);
}

export async function fetchBuildRecipes(workspaceId: string): Promise<ModelBuildRecipe[]> {
  return apiGet<ModelBuildRecipe[]>(`/workspaces/${workspaceId}/model-building/recipes`);
}

export async function runBuildPreflight(
  workspaceId: string,
  req: BuildPreflightRequest
): Promise<BuildPreflightResponse> {
  return apiPost<BuildPreflightResponse>(
    `/workspaces/${workspaceId}/model-building/preflight`,
    req
  );
}

export async function createExternalAuthorization(
  workspaceId: string,
  req: CreateExternalAuthorizationRequest
): Promise<ExternalAuthorization> {
  return apiPost<ExternalAuthorization>(
    `/workspaces/${workspaceId}/model-building/authorizations/external-processing`,
    req
  );
}

export async function fetchExternalAuthorizations(
  workspaceId: string
): Promise<ExternalAuthorization[]> {
  return apiGet<ExternalAuthorization[]>(
    `/workspaces/${workspaceId}/model-building/authorizations/external-processing`
  );
}

export async function createBuildRun(
  workspaceId: string,
  req: CreateModelBuildRunRequest
): Promise<ModelBuildRun> {
  return apiPost<ModelBuildRun>(`/workspaces/${workspaceId}/model-building/runs`, req);
}

export async function fetchBuildRuns(
  workspaceId: string,
  statusFilter?: string
): Promise<ModelBuildRun[]> {
  const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
  return apiGet<ModelBuildRun[]>(`/workspaces/${workspaceId}/model-building/runs${query}`);
}

export async function fetchBuildRun(
  workspaceId: string,
  runId: string
): Promise<ModelBuildRun> {
  return apiGet<ModelBuildRun>(`/workspaces/${workspaceId}/model-building/runs/${runId}`);
}

export async function executeLocalSmokeTest(
  workspaceId: string,
  runId: string
): Promise<ModelBuildRun> {
  return apiPost<ModelBuildRun>(
    `/workspaces/${workspaceId}/model-building/runs/${runId}/execute-smoke-test`,
    {}
  );
}

export async function downloadColabNotebook(
  workspaceId: string,
  runId: string
): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>(
    `/workspaces/${workspaceId}/model-building/runs/${runId}/export-colab`
  );
}

export async function importColabResult(
  workspaceId: string,
  runId: string,
  req: ColabResultImportRequest
): Promise<StagedArtifact> {
  return apiPost<StagedArtifact>(
    `/workspaces/${workspaceId}/model-building/runs/${runId}/import-colab-result`,
    req
  );
}

export async function linkModelEvaluation(
  workspaceId: string,
  runId: string,
  req: {
    staged_artifact_id: string;
    evaluation_run_id: string;
    model_role: string;
    base_evaluation_score?: number;
  }
): Promise<ModelEvaluationLink> {
  return apiPost<ModelEvaluationLink>(
    `/workspaces/${workspaceId}/model-building/runs/${runId}/link-evaluation`,
    req
  );
}
