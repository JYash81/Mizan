import { apiGet, apiPost } from "../../lib/api/client";
import type {
  AppDefinition,
  AppListingDetail,
  AppListingSummary,
  CreateAppDefinitionRequest,
  CreateAppListingRequest,
  CreateAppVersionRequest,
  CreateModelListingRequest,
  DownloadAuthorizationResponse,
  ModelListingDetail,
  ModelListingSummary,
  PaginatedResponse,
  ReviewListingRequest,
  SuspendListingRequest,
} from "./types";

// =========================================================================
// Model Zoo Public / Cross-Workspace Discovery
// =========================================================================

export async function discoverModels(params: {
  query?: string;
  category?: string;
  visibility?: string;
  hardware_badge?: string;
  sort_by?: string;
  sort_dir?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ModelListingSummary>> {
  const queryParts: string[] = [];
  if (params.query) queryParts.push(`query=${encodeURIComponent(params.query)}`);
  if (params.category) queryParts.push(`category=${encodeURIComponent(params.category)}`);
  if (params.visibility) queryParts.push(`visibility=${encodeURIComponent(params.visibility)}`);
  if (params.hardware_badge) queryParts.push(`hardware_badge=${encodeURIComponent(params.hardware_badge)}`);
  if (params.sort_by) queryParts.push(`sort_by=${encodeURIComponent(params.sort_by)}`);
  if (params.sort_dir) queryParts.push(`sort_dir=${encodeURIComponent(params.sort_dir)}`);
  if (params.page) queryParts.push(`page=${params.page}`);
  if (params.page_size) queryParts.push(`page_size=${params.page_size}`);

  const qs = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
  return apiGet<PaginatedResponse<ModelListingSummary>>(`/zoo/models${qs}`);
}

export async function getModelDetail(listingId: string): Promise<ModelListingDetail> {
  return apiGet<ModelListingDetail>(`/zoo/models/${listingId}`);
}

export async function authorizeModelArtifactDownload(
  workspaceId: string,
  listingId: string,
  artifactId: string
): Promise<DownloadAuthorizationResponse> {
  return apiPost<DownloadAuthorizationResponse>(
    `/workspaces/${workspaceId}/model-zoo/listings/${listingId}/artifacts/${artifactId}/download`,
    {}
  );
}

// =========================================================================
// Workspace Model Listings (Publishing / Moderation)
// =========================================================================

export async function fetchWorkspaceModelListings(
  workspaceId: string,
  params?: { status?: string }
): Promise<ModelListingSummary[]> {
  const qs = params?.status ? `?status=${encodeURIComponent(params.status)}` : "";
  return apiGet<ModelListingSummary[]>(`/workspaces/${workspaceId}/model-zoo/listings${qs}`);
}

export async function createModelListing(
  workspaceId: string,
  req: CreateModelListingRequest
): Promise<ModelListingSummary> {
  return apiPost<ModelListingSummary>(`/workspaces/${workspaceId}/model-zoo/listings`, req);
}

export async function submitModelListing(
  workspaceId: string,
  listingId: string
): Promise<{ message: string }> {
  return apiPost<{ message: string }>(
    `/workspaces/${workspaceId}/model-zoo/listings/${listingId}/submit`,
    {}
  );
}

export async function reviewModelListing(
  workspaceId: string,
  listingId: string,
  req: ReviewListingRequest
): Promise<ModelListingSummary> {
  return apiPost<ModelListingSummary>(
    `/workspaces/${workspaceId}/model-zoo/listings/${listingId}/review`,
    req
  );
}

export async function suspendModelListing(
  workspaceId: string,
  listingId: string,
  req: SuspendListingRequest
): Promise<ModelListingSummary> {
  return apiPost<ModelListingSummary>(
    `/workspaces/${workspaceId}/model-zoo/listings/${listingId}/suspend`,
    req
  );
}

// =========================================================================
// App Zoo Discovery & Management
// =========================================================================

export async function discoverApps(params: {
  query?: string;
  category?: string;
  visibility?: string;
  sort_by?: string;
  sort_dir?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<AppListingSummary>> {
  const queryParts: string[] = [];
  if (params.query) queryParts.push(`query=${encodeURIComponent(params.query)}`);
  if (params.category) queryParts.push(`category=${encodeURIComponent(params.category)}`);
  if (params.visibility) queryParts.push(`visibility=${encodeURIComponent(params.visibility)}`);
  if (params.sort_by) queryParts.push(`sort_by=${encodeURIComponent(params.sort_by)}`);
  if (params.sort_dir) queryParts.push(`sort_dir=${encodeURIComponent(params.sort_dir)}`);
  if (params.page) queryParts.push(`page=${params.page}`);
  if (params.page_size) queryParts.push(`page_size=${params.page_size}`);

  const qs = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
  return apiGet<PaginatedResponse<AppListingSummary>>(`/zoo/apps${qs}`);
}

export async function getAppDetail(listingId: string): Promise<AppListingDetail> {
  return apiGet<AppListingDetail>(`/zoo/apps/${listingId}`);
}

export async function fetchWorkspaceAppDefinitions(
  workspaceId: string
): Promise<AppDefinition[]> {
  return apiGet<AppDefinition[]>(`/workspaces/${workspaceId}/app-zoo/definitions`);
}

export async function createAppDefinition(
  workspaceId: string,
  req: CreateAppDefinitionRequest
): Promise<AppDefinition> {
  return apiPost<AppDefinition>(`/workspaces/${workspaceId}/app-zoo/definitions`, req);
}

export async function createAppVersion(
  workspaceId: string,
  definitionId: string,
  req: CreateAppVersionRequest
): Promise<AppDefinition> {
  return apiPost<AppDefinition>(
    `/workspaces/${workspaceId}/app-zoo/definitions/${definitionId}/versions`,
    req
  );
}

export async function fetchWorkspaceAppListings(
  workspaceId: string,
  params?: { status?: string }
): Promise<AppListingSummary[]> {
  const qs = params?.status ? `?status=${encodeURIComponent(params.status)}` : "";
  return apiGet<AppListingSummary[]>(`/workspaces/${workspaceId}/app-zoo/listings${qs}`);
}

export async function createAppListing(
  workspaceId: string,
  req: CreateAppListingRequest
): Promise<AppListingSummary> {
  return apiPost<AppListingSummary>(`/workspaces/${workspaceId}/app-zoo/listings`, req);
}

export async function submitAppListing(
  workspaceId: string,
  listingId: string
): Promise<{ message: string }> {
  return apiPost<{ message: string }>(
    `/workspaces/${workspaceId}/app-zoo/listings/${listingId}/submit`,
    {}
  );
}

export async function reviewAppListing(
  workspaceId: string,
  listingId: string,
  req: ReviewListingRequest
): Promise<AppListingSummary> {
  return apiPost<AppListingSummary>(
    `/workspaces/${workspaceId}/app-zoo/listings/${listingId}/review`,
    req
  );
}

export async function suspendAppListing(
  workspaceId: string,
  listingId: string,
  req: SuspendListingRequest
): Promise<AppListingSummary> {
  return apiPost<AppListingSummary>(
    `/workspaces/${workspaceId}/app-zoo/listings/${listingId}/suspend`,
    req
  );
}
