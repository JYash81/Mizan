"""Pydantic schemas for Evaluation Runs, Results, and Metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.evaluation import (
    EvaluationRunStatus,
    EvaluationTargetType,
    MetricStatus,
)


class EvaluationRunCreate(BaseModel):
    suite_id: str
    suite_version_id: str | None = None
    rubric_id: str | None = None
    target_type: EvaluationTargetType = EvaluationTargetType.RAG_PIPELINE
    target_name: str = Field("default-rag", max_length=255)
    provider_name: str = Field("mock", max_length=64)
    model_name: str = Field("mock-gpt-mizan-v1", max_length=128)
    retrieval_config: dict[str, Any] = Field(default_factory=dict)
    supplied_responses: dict[str, Any] | None = None  # case_id -> answer/dict mapping if target is SUPPLIED_RESPONSES or MOCK_LLM


class EvaluationMetricResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_result_id: str
    metric_key: str
    raw_score: float
    normalized_score: float
    score_scale: str
    status: MetricStatus
    evaluator_version: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class EvaluationCaseResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    case_id: str
    actual_answer: str | None
    actual_answer_digest: str | None
    overall_case_score: float
    status: str
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float
    created_at: datetime
    metrics: list[EvaluationMetricResultResponse] = Field(default_factory=list)


class EvaluationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    suite_id: str
    suite_version_id: str
    rubric_id: str | None
    rubric_version: int
    target_type: EvaluationTargetType
    target_name: str
    provider_name: str
    model_name: str
    retrieval_config: dict[str, Any] = Field(default_factory=dict)
    status: EvaluationRunStatus
    total_cases: int
    completed_cases: int
    failed_cases: int
    passed_cases: int = 0
    overall_score: float | None
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    metric_summary: dict[str, float] = Field(default_factory=dict)
    case_results: list[EvaluationCaseResultResponse] = Field(default_factory=list)
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by: str
    created_at: datetime
