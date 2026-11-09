"""Pydantic schemas for experiments and trial matrix generation."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.evaluation import SplitType
from app.models.experiment import ExperimentStatus
from app.modules.experiments.schemas.trial import ExperimentTrialResponse, TrialConfig


class MatrixGenerateStrategy(str, enum.Enum):
    MANUAL = "MANUAL"
    PARAMETRIC_VARIATION = "PARAMETRIC_VARIATION"
    PRESET_MATRIX = "PRESET_MATRIX"


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    dataset_id: str
    dataset_version_id: str
    evaluation_suite_id: str
    evaluation_suite_version_id: str
    evaluation_split: SplitType = Field(default=SplitType.VALIDATION)
    baseline_config: TrialConfig = Field(default_factory=TrialConfig)

    @field_validator("evaluation_split")
    @classmethod
    def validate_split(cls, split: SplitType) -> SplitType:
        # Holdout protection invariant: Ordinary experiment tuning cannot target HOLDOUT split
        if split == SplitType.HOLDOUT:
            raise ValueError(
                "Experiment tuning cannot target the HOLDOUT split. "
                "The holdout set is reserved strictly for final un-tuned verification."
            )
        return split


class ExperimentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class MatrixGenerateRequest(BaseModel):
    strategy: MatrixGenerateStrategy = Field(default=MatrixGenerateStrategy.PRESET_MATRIX)
    preset_name: str | None = Field(
        default="chunk_sensitivity",
        description="Name of preset: 'chunk_sensitivity', 'retrieval_depth', or 'prompt_strategy'",
    )
    variations: dict[str, list[Any]] | None = Field(
        default=None,
        description="Dictionary mapping configuration fields to lists of candidate values",
    )
    manual_trials: list[TrialConfig] | None = Field(
        default=None,
        description="Explicit list of 3 to 9 trial configurations",
    )


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    name: str
    slug: str
    description: str | None = None
    status: ExperimentStatus
    dataset_id: str
    dataset_version_id: str
    gate1_approval_id: str | None = None
    dataset_digest: str | None = None
    evaluation_suite_id: str
    evaluation_suite_version_id: str
    canonical_suite_digest: str | None = None
    evaluation_split: SplitType
    baseline_config: dict[str, Any] = Field(default_factory=dict)
    configuration_digest: str | None = None
    total_trials: int = 0
    completed_trials: int = 0
    failed_trials: int = 0
    cancelled_trials: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancellation_requested_at: datetime | None = None
    error_message: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    trials: list[ExperimentTrialResponse] = Field(default_factory=list)
