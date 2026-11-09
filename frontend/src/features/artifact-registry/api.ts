import { apiGet, apiPost } from "../../lib/api/client";
import type {
  CreateModelFamilyRequest,
  CreateModelVersionRequest,
  FinalizeManifestResponse,
  Gate3Approval,
  Gate3DecisionRequest,
  Gate3Revocation,
  Gate3RevokeRequest,
  Gate3SignatureVerifyResponse,
  ModelFamily,
  ModelVersion,
  RegisteredArtifact,
  RegisterStagedArtifactRequest,
} from "./types";

export async function fetchModelFamilies(workspaceId: string): Promise<ModelFamily[]> {
  return apiGet<ModelFamily[]>(`/workspaces/${workspaceId}/artifact-registry/families`);
}

export async function createModelFamily(
  workspaceId: string,
  req: CreateModelFamilyRequest
): Promise<ModelFamily> {
  return apiPost<ModelFamily>(`/workspaces/${workspaceId}/artifact-registry/families`, req);
}

export async function fetchModelFamily(
  workspaceId: string,
  familyId: string
): Promise<ModelFamily> {
  return apiGet<ModelFamily>(`/workspaces/${workspaceId}/artifact-registry/families/${familyId}`);
}

export async function createModelVersion(
  workspaceId: string,
  familyId: string,
  req: CreateModelVersionRequest
): Promise<ModelVersion> {
  return apiPost<ModelVersion>(
    `/workspaces/${workspaceId}/artifact-registry/families/${familyId}/versions`,
    req
  );
}

export async function fetchModelVersion(
  workspaceId: string,
  versionId: string
): Promise<ModelVersion> {
  return apiGet<ModelVersion>(`/workspaces/${workspaceId}/artifact-registry/versions/${versionId}`);
}

export async function registerStagedArtifact(
  workspaceId: string,
  versionId: string,
  req: RegisterStagedArtifactRequest
): Promise<RegisteredArtifact> {
  return apiPost<RegisteredArtifact>(
    `/workspaces/${workspaceId}/artifact-registry/versions/${versionId}/register-staged-artifact`,
    req
  );
}

export async function finalizeModelVersionManifest(
  workspaceId: string,
  versionId: string
): Promise<FinalizeManifestResponse> {
  return apiPost<FinalizeManifestResponse>(
    `/workspaces/${workspaceId}/artifact-registry/versions/${versionId}/finalize-manifest`,
    {}
  );
}

export async function fetchGate3Approvals(workspaceId: string): Promise<Gate3Approval[]> {
  return apiGet<Gate3Approval[]>(`/workspaces/${workspaceId}/gate3/approvals`);
}

export async function fetchGate3Approval(
  workspaceId: string,
  versionId: string
): Promise<Gate3Approval> {
  return apiGet<Gate3Approval>(`/workspaces/${workspaceId}/gate3/approvals/${versionId}`);
}

export async function submitGate3Decision(
  workspaceId: string,
  versionId: string,
  req: Gate3DecisionRequest
): Promise<Gate3Approval> {
  return apiPost<Gate3Approval>(
    `/workspaces/${workspaceId}/gate3/approvals/${versionId}/decide`,
    req
  );
}

export async function revokeModelRelease(
  workspaceId: string,
  versionId: string,
  req: Gate3RevokeRequest
): Promise<Gate3Revocation> {
  return apiPost<Gate3Revocation>(
    `/workspaces/${workspaceId}/gate3/approvals/${versionId}/revoke`,
    req
  );
}

export async function verifyGate3Signature(
  workspaceId: string,
  versionId: string
): Promise<Gate3SignatureVerifyResponse> {
  return apiGet<Gate3SignatureVerifyResponse>(
    `/workspaces/${workspaceId}/gate3/approvals/${versionId}/verify-signature`
  );
}
