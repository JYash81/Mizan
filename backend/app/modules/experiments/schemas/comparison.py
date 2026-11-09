"""Pydantic schemas for multi-trial factual comparison (Milestone 7).

NOTE: Under M7 boundaries, this model presents strictly factual comparisons
(e.g. highest observed score for a metric, observed latency differences).
It contains zero M9 recommendation logic (no Pareto frontiers, no automated winner claims).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TrialComparisonSummary(BaseModel):
    """Normalized snapshot of a trial's configuration and measured results."""

    trial_id: str
    trial_number: int
    name: str
    status: str
    configuration: dict[str, Any]
    configuration_digest: str
    evaluation_run_id: str | None = None
    aggregate_score: float | None = None
    metric_scores: dict[str, float | None] = Field(
        default_factory=dict,
        description="Metric key to score mapping. Missing metrics are preserved as None, never 0.0.",
    )
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_p99_ms: float | None = None
    execution_duration_ms: float | None = None
    error_summary: str | None = None


class MetricObservation(BaseModel):
    """Factual observation for an individual metric across completed trials."""

    metric_key: str
    highest_observed_score: float | None = None
    highest_scoring_trials: list[int] = Field(default_factory=list)
    lowest_observed_score: float | None = None
    mean_observed_score: float | None = None


class ExperimentComparisonResponse(BaseModel):
    """Complete multi-trial comparison report for an experiment."""

    model_config = ConfigDict(from_attributes=True)

    experiment_id: str
    experiment_name: str
    status: str
    dataset_version_id: str
    evaluation_suite_version_id: str
    evaluation_split: str
    total_trials: int
    completed_trials: int
    failed_trials: int
    trials: list[TrialComparisonSummary]
    metric_keys: list[str] = Field(
        default_factory=list,
        description="All aligned metric keys across trials (e.g. 11 deterministic M6 metrics)",
    )
    metric_observations: list[MetricObservation] = Field(default_factory=list)
    lowest_observed_latency_ms: float | None = None
    lowest_latency_trials: list[int] = Field(default_factory=list)
    compatibility_verified: bool = True
    compatibility_notes: list[str] = Field(default_factory=list)
