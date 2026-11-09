import { apiGet, apiPost } from "../../lib/api/client";
import type {
  ProviderInfo,
  RAGEvalResponse,
  RAGIndexResponse,
  RAGQueryResponse,
  RetrievedChunk,
} from "./types";

export async function fetchProviders(workspaceId: string): Promise<ProviderInfo[]> {
  return apiGet<ProviderInfo[]>(`/workspaces/${workspaceId}/rag/providers`);
}

export async function indexDatasetVersion(
  workspaceId: string,
  datasetVersionId: string,
  chunkSizeChars: number = 500,
  chunkOverlapChars: number = 100
): Promise<RAGIndexResponse> {
  return apiPost<RAGIndexResponse>(`/workspaces/${workspaceId}/rag/index`, {
    dataset_version_id: datasetVersionId,
    chunk_size_chars: chunkSizeChars,
    chunk_overlap_chars: chunkOverlapChars,
  });
}

export async function queryRAG(
  workspaceId: string,
  params: {
    query: string;
    dataset_version_id?: string;
    provider?: string;
    top_k?: number;
    score_threshold?: number;
  }
): Promise<RAGQueryResponse> {
  return apiPost<RAGQueryResponse>(`/workspaces/${workspaceId}/rag/query`, params);
}

export async function evaluateRAG(
  workspaceId: string,
  params: {
    query: string;
    answer: string;
    retrieved_chunks: RetrievedChunk[] | Array<Record<string, unknown>>;
    expected_keywords?: string[];
  }
): Promise<RAGEvalResponse> {
  return apiPost<RAGEvalResponse>(`/workspaces/${workspaceId}/rag/evaluate`, params);
}
