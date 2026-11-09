"""Pydantic schemas for Evaluation Rubrics and Criteria."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.evaluation import ScoringMethod


class RubricCriterionCreate(BaseModel):
    criterion_key: str | None = None
    metric_name: str | None = None
    name: str | None = None
    description: str | None = None
    scoring_method: ScoringMethod | None = None
    maximum_score: float = Field(100.0, gt=0.0)
    weight: float = Field(1.0, ge=0.0)
    minimum_acceptable_score: float = Field(70.0, ge=0.0)
    min_acceptable_score: float | None = None
    is_critical: bool = False
    configuration: dict[str, Any] = Field(default_factory=dict)


class EvaluationRubricCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: str | None = Field(None, max_length=2000)
    domain: str = Field("general", max_length=100)
    is_default: bool = False
    criteria: list[RubricCriterionCreate] = Field(default_factory=list)


class RubricCriterionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rubric_id: str
    criterion_key: str
    name: str
    description: str
    scoring_method: ScoringMethod
    maximum_score: float
    weight: float
    minimum_acceptable_score: float
    configuration: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class EvaluationRubricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    name: str
    description: str | None
    version: int
    domain: str
    is_default: bool
    created_by: str
    created_at: datetime
    criteria: list[RubricCriterionResponse] = Field(default_factory=list)
