export interface ProviderInfo {
  provider_name: string;
  is_available: boolean;
  is_free: boolean;
  status_message: string;
  cost_per_million_input_cents: number;
  cost_per_million_output_cents: number;
}

export interface Citation {
  citation_marker: string;
  document_id: string;
  chunk_index: number;
  score: number;
  snippet: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  score: number;
  text: string;
  payload: Record<string, unknown>;
}

export interface RAGMetrics {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost_cents: number;
}

export interface RAGQueryResponse {
  query: string;
  answer: string;
  citations: Citation[];
  retrieved_chunks: RetrievedChunk[];
  metrics: RAGMetrics;
  provider: {
    name: string;
    model: string;
  };
}

export interface RAGEvalResponse {
  query: string;
  retrieval_recall: number;
  context_relevance: number;
  faithfulness: number;
  citation_completeness: number;
  overall_score: number;
  citations_count: number;
  retrieved_chunks_count: number;
  details: Record<string, unknown>;
}

export interface RAGIndexResponse {
  workspace_id: string;
  dataset_version_id: string;
  approval_id: string;
  collection_name: string;
  documents_indexed: number;
  chunks_indexed: number;
  embedding_model: string;
}
