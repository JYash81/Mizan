"""Pydantic schemas for RAG operations and AI provider interactions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RAGIndexRequest(BaseModel):
    dataset_version_id: str
    chunk_size_chars: int = Field(500, ge=100, le=4000)
    chunk_overlap_chars: int = Field(100, ge=0, le=1000)


class RAGIndexResponse(BaseModel):
    workspace_id: str
    dataset_version_id: str
    approval_id: str
    collection_name: str
    documents_indexed: int
    chunks_indexed: int
    embedding_model: str


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    dataset_version_id: str | None = None
    top_k: int = Field(4, ge=1, le=20)
    score_threshold: float = Field(0.2, ge=0.0, le=1.0)
    provider: str | None = Field("mock", max_length=64)


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[dict[str, Any]]
    retrieved_chunks: list[dict[str, Any]]
    metrics: dict[str, Any]
    provider: dict[str, str]


class RAGEvalRequest(BaseModel):
    query: str
    answer: str
    retrieved_chunks: list[dict[str, Any]]
    expected_keywords: list[str] | None = None


class RAGEvalResponse(BaseModel):
    query: str
    retrieval_recall: float
    context_relevance: float
    faithfulness: float
    citation_completeness: float
    overall_score: float
    citations_count: int
    retrieved_chunks_count: int
    details: dict[str, Any]


class ProviderInfoResponse(BaseModel):
    provider_name: str
    is_available: bool
    is_free: bool
    status_message: str
    cost_per_million_input_cents: float = 0.0
    cost_per_million_output_cents: float = 0.0
