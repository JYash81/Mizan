"""Pydantic schemas for Evaluation Suite and Version management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.evaluation import EvaluationSuiteStatus, SuiteVersionStatus


class EvaluationSuiteCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    slug: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    domain: str = Field("general", max_length=100)
    suite_type: str | None = None
    language: str = Field("en", min_length=2, max_length=10)
    tags: list[str] | None = None
    source_dataset_id: str | None = None
    source_dataset_version_id: str | None = None
    gate1_approval_id: str | None = None


class EvaluationSuiteUpdate(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = Field(None, max_length=2000)
    domain: str | None = Field(None, max_length=100)
    status: EvaluationSuiteStatus | None = None


class GenerateExamRequest(BaseModel):
    dataset_version_id: str
    target_question_count: int = Field(10, ge=1, le=50)
    target_count: int | None = None
    language: str = Field("en", min_length=2, max_length=10)
    difficulty_distribution: dict[str, float] | None = None
    categories: list[str] | None = None
    include_unanswerable: bool = True
    generator_type: str | None = None
    generation_method: str = Field("rule_based", max_length=64)


class FinalizeSuiteRequest(BaseModel):
    rubric_id: str | None = None


class EvaluationSuiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    name: str
    slug: str
    description: str | None
    domain: str
    language: str
    source_dataset_id: str | None
    source_dataset_version_id: str | None
    gate1_approval_id: str | None
    generation_method: str
    status: EvaluationSuiteStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    case_count: int = 0
    total_cases: int = 0
    active_version: int | None = None


class EvaluationSuiteVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_id: str | None = None
    suite_id: str
    version_number: int
    suite_digest: str
    case_count: int
    rubric_id: str | None
    rubric_version: int
    source_dataset_version_id: str | None
    source_dataset_digest: str | None
    gate1_approval_id: str | None
    generation_config_digest: str | None
    status: SuiteVersionStatus
    created_by: str
    created_at: datetime
