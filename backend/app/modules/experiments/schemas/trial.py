"""Pydantic schemas for experiment trials."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.experiment import TrialStatus


class TrialConfig(BaseModel):
    """Validated configuration for a single experiment trial."""

    model_config = ConfigDict(extra="ignore")

    chunk_size_chars: int = Field(default=500, ge=50, le=5000, description="Chunk length in characters")
    chunk_overlap_chars: int = Field(default=100, ge=0, le=1000, description="Chunk overlap in characters")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of retrieved chunks")
    retrieval_strategy: str = Field(default="cosine_dense", description="Retrieval similarity algorithm")
    embedding_provider: str = Field(default="fastembed", description="Embedding provider name")
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="Embedding model name or identifier",
    )
    prompt_strategy: str = Field(default="standard_qa", description="Prompt assembly strategy")
    provider_name: str = Field(default="mock", description="LLM provider name")
    model_name: str = Field(default="mock-generator-v1", description="LLM model identifier")
    generation_params: dict[str, Any] = Field(default_factory=dict, description="Generation hyperparameters")

    @field_validator("chunk_overlap_chars")
    @classmethod
    def validate_overlap(cls, overlap: int, info: Any) -> int:
        chunk_size = info.data.get("chunk_size_chars", 500)
        if overlap >= chunk_size:
            raise ValueError(f"chunk_overlap_chars ({overlap}) must be less than chunk_size_chars ({chunk_size})")
        return overlap

    @field_validator("provider_name")
    @classmethod
    def validate_provider(cls, val: str) -> str:
        allowed = {"mock", "ollama", "gemini_free"}
        if val.lower() not in allowed:
            raise ValueError(f"Provider '{val}' is not supported under Free-Only policy. Permitted: {allowed}")
        return val.lower()

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedder(cls, val: str) -> str:
        allowed = {"fastembed", "mock"}
        if val.lower() not in allowed:
            raise ValueError(f"Embedding provider '{val}' is not supported. Permitted: {allowed}")
        return val.lower()


class ExperimentTrialCreate(BaseModel):
    trial_number: int = Field(ge=1, le=9)
    name: str = Field(min_length=1, max_length=255)
    configuration: TrialConfig


class ExperimentTrialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    experiment_id: str
    trial_number: int
    name: str
    status: TrialStatus
    configuration_json: str
    configuration_digest: str
    evaluation_run_id: str | None = None
    aggregate_score: float | None = None
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_p99_ms: float | None = None
    execution_duration_ms: float | None = None
    error_code: str | None = None
    error_summary: str | None = None
    retry_count: int = 0
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
