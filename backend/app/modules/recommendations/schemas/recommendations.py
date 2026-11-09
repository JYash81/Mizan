"""Pydantic V2 Schemas for Mizan Milestone 9 Recommendation Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.recommendations import (
    CandidateEligibilityStatus,
    CandidateProvenanceStatus,
    RecommendationDecisionType,
    RecommendationRunStatus,
)


class CreateOptimizationProfileRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    objectives: list[str] = Field(default_factory=lambda: ["aggregate_score", "latency_p95_ms", "required_ram_mb"])
    weights: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    preferred_hardware_profile: str | None = None
    budget_currency: str = Field(default="USD", max_length=8)


class UpdateOptimizationProfileRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    objectives: list[str] | None = None
    weights: dict[str, float] | None = None
    constraints: dict[str, Any] | None = None
    preferred_hardware_profile: str | None = None
    budget_currency: str | None = None


class OptimizationProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    name: str
    description: str | None
    objectives: list[str]
    weights: dict[str, float]
    constraints: dict[str, Any]
    preferred_hardware_profile: str | None
    budget_currency: str
    version: int
    created_by: str
    updated_by: str | None
    created_at: datetime
    updated_at: datetime


class CreateRecommendationRunRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    experiment_ids: list[str] = Field(..., min_length=1)
    trial_ids: list[str] | None = None
    optimization_profile_id: str | None = None
    selected_objectives: list[str] = Field(
        default_factory=lambda: ["aggregate_score", "latency_p95_ms", "required_ram_mb"]
    )
    weights: dict[str, float] | None = None
    hard_constraints: dict[str, Any] = Field(default_factory=dict)


class RecordDecisionRequest(BaseModel):
    selected_candidate_id: str | None = None
    decision: RecommendationDecisionType
    decision_reason: str = Field(..., min_length=3)


class RecommendationDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recommendation_run_id: str
    selected_candidate_id: str | None
    decision: RecommendationDecisionType
    decision_reason: str
    actor_id: str
    created_at: datetime


class RecommendationScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recommendation_run_id: str
    scenario_name: str
    weight_snapshot: dict[str, float]
    ranking_snapshot: Any
    explanation: str | None
    created_at: datetime


class RecommendationCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recommendation_run_id: str
    experiment_id: str
    experiment_trial_id: str
    candidate_label: str
    configuration_digest: str
    evaluation_run_id: str | None
    dataset_id: str | None
    dataset_version_id: str | None
    evaluation_suite_id: str | None
    evaluation_suite_version_id: str | None
    evaluation_split: str | None
    hardware_profile_key: str | None
    provenance_status: CandidateProvenanceStatus
    eligibility_status: CandidateEligibilityStatus
    exclusion_reasons: list[str]
    objective_values: dict[str, Any]
    normalized_objective_values: dict[str, float | None]
    constraint_results: dict[str, Any]
    pareto_frontier_member: bool
    dominated_by: list[str]
    dominates: list[str]
    weighted_score: float | None
    evidence_summary: dict[str, str]
    explanation_text: str | None
    created_at: datetime


class RecommendationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    name: str
    description: str | None
    status: RecommendationRunStatus
    algorithm_version: str
    input_digest: str
    result_digest: str | None
    total_candidates: int
    eligible_candidates: int
    frontier_candidates: int
    error_summary: str | None
    created_by: str
    created_at: datetime
    completed_at: datetime | None
    candidates: list[RecommendationCandidateResponse] = Field(default_factory=list)
    decisions: list[RecommendationDecisionResponse] = Field(default_factory=list)
    scenarios: list[RecommendationScenarioResponse] = Field(default_factory=list)


class RecommendationRunSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str
    name: str
    description: str | None
    status: RecommendationRunStatus
    algorithm_version: str
    input_digest: str
    result_digest: str | None
    total_candidates: int
    eligible_candidates: int
    frontier_candidates: int
    created_by: str
    created_at: datetime
    completed_at: datetime | None


class RecommendationRunListResponse(BaseModel):
    items: list[RecommendationRunSummaryResponse]
    total: int


class CandidateValidationRequest(BaseModel):
    experiment_ids: list[str] = Field(default_factory=list)
    trial_ids: list[str] | None = None


class CandidateValidationResult(BaseModel):
    trial_id: str
    experiment_id: str
    trial_number: int
    candidate_label: str
    trial_status: str
    configuration_digest: str
    is_eligible: bool
    exclusion_reasons: list[str]
    provenance_status: CandidateProvenanceStatus
