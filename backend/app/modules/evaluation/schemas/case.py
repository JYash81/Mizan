"""Pydantic schemas for Evaluation Case and Review."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.evaluation import (
    CaseCategory,
    DifficultyLevel,
    GroundTruthStatus,
    ReviewDecision,
    SplitType,
)


class EvaluationCaseCreateManual(BaseModel):
    category: CaseCategory = CaseCategory.FACTUAL
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    split: SplitType = SplitType.DEVELOPMENT
    language: str = Field("en", min_length=2, max_length=10)
    question: str = Field(..., min_length=5, max_length=2000)
    expected_answer: str = Field(..., min_length=1, max_length=5000)
    is_unanswerable: bool = False
    keywords: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    reviewer_notes: str | None = Field(None, max_length=1000)


class EvaluationCaseUpdate(BaseModel):
    question: str | None = Field(None, min_length=5, max_length=2000)
    expected_answer: str | None = Field(None, min_length=1, max_length=5000)
    category: CaseCategory | None = None
    difficulty: DifficultyLevel | None = None
    split: SplitType | None = None
    is_unanswerable: bool | None = None
    reviewer_notes: str | None = Field(None, max_length=1000)


class EvaluationCaseReviewAction(BaseModel):
    decision: ReviewDecision
    comments: str | None = Field(None, max_length=1000)
    corrected_question: str | None = None
    corrected_expected_answer: str | None = None
    updated_expected_answer: str | None = None
    corrected_difficulty: DifficultyLevel | None = None
    corrected_category: CaseCategory | None = None


class EvaluationCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    suite_id: str
    suite_version_id: str | None
    case_type: str
    category: CaseCategory
    difficulty: DifficultyLevel
    split: SplitType
    language: str
    question: str
    expected_answer: str
    is_unanswerable: bool
    source_document_ids: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    ground_truth_status: GroundTruthStatus
    generation_method: str
    reviewer_notes: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class EvaluationReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    case_id: str
    reviewer_user_id: str
    decision: ReviewDecision
    previous_status: str
    new_status: str
    comments: str | None
    created_at: datetime
