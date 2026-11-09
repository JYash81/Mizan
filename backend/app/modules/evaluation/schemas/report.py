"""Pydantic schemas for Evaluation Reports."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationReportSummary(BaseModel):
    run_id: str
    suite_id: str
    suite_name: str
    suite_version_number: int
    suite_digest: str
    target_name: str
    provider_name: str
    model_name: str
    status: str
    total_cases: int
    completed_cases: int
    failed_cases: int
    overall_score: float
    score_interpretation: str
    criterion_averages: dict[str, float] = Field(default_factory=dict)
    category_averages: dict[str, float] = Field(default_factory=dict)
    difficulty_averages: dict[str, float] = Field(default_factory=dict)
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: float = 0.0


class EvaluationCaseReportItem(BaseModel):
    case_id: str
    question: str
    expected_answer: str
    actual_answer: str | None
    is_unanswerable: bool
    category: str
    difficulty: str
    overall_case_score: float
    status: str
    metrics: dict[str, float] = Field(default_factory=dict)
    citations_count: int = 0
    retrieved_chunks_count: int = 0
    latency_ms: float = 0.0


class FullEvaluationReport(BaseModel):
    summary: EvaluationReportSummary
    cases: list[EvaluationCaseReportItem] = Field(default_factory=list)
    run_id: str | None = None
    suite_name: str | None = None
    interpretation: str | None = None
    limitations_disclaimer: str = (
        "Mizan evaluation metrics are deterministic and evidence-grounded. Heuristic metrics (such as lexical relevance or keyword coverage) "
        "measure proxy behavior and do not constitute an infallible claim of semantic reasoning or regulatory legal certification."
    )
