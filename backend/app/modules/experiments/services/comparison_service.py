"""Comparison Service for multi-trial factual analysis and metric alignment.

STRICT MILESTONE 7 SCOPE:
- Bounded, factual observations only.
- Missing metric values are preserved as None, never replaced with 0.0.
- Strict rejection of M9 recommendation logic: no Pareto optimization,
  no weighted aggregate ranking, no 'best model' declarations.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.models.experiment import TrialStatus
from app.modules.experiments.repositories.experiment_repository import ExperimentRepository
from app.modules.experiments.schemas.comparison import (
    ExperimentComparisonResponse,
    MetricObservation,
    TrialComparisonSummary,
)

logger = logging.getLogger(__name__)


class ExperimentComparisonService:
    def __init__(self, experiment_repo: ExperimentRepository | None = None):
        self.experiment_repo = experiment_repo or ExperimentRepository()

    def generate_comparison(
        self,
        db: Session,
        workspace_id: str,
        experiment_id: str,
    ) -> ExperimentComparisonResponse:
        """Align trials, metrics, and factual observations across an experiment."""
        experiment = self.experiment_repo.get_experiment(db, experiment_id, workspace_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found in workspace.")

        trials = self.experiment_repo.list_trials(db, experiment.id)

        # 1. Check provenance compatibility
        compatibility_notes: list[str] = []
        is_compatible = True

        if not experiment.evaluation_suite_version_id:
            compatibility_notes.append("Experiment lacks a frozen evaluation_suite_version_id.")
            is_compatible = False

        # 2. Collect all metric keys across completed trials
        all_metric_keys_set: set[str] = set()
        raw_trial_metrics: list[dict[str, float]] = []

        for trial in trials:
            breakdown: dict[str, float] = {}
            if trial.score_breakdown_json:
                try:
                    breakdown = json.loads(trial.score_breakdown_json)
                except Exception:
                    pass
            raw_trial_metrics.append(breakdown)
            all_metric_keys_set.update(breakdown.keys())

        sorted_metric_keys = sorted(all_metric_keys_set)

        # 3. Construct normalized trial comparison summaries
        trial_summaries: list[TrialComparisonSummary] = []
        completed_trial_latencies: list[tuple[int, float]] = []

        for trial, breakdown in zip(trials, raw_trial_metrics, strict=True):
            # Align metric scores: if missing, keep None
            aligned_scores: dict[str, float | None] = {}
            for k in sorted_metric_keys:
                aligned_scores[k] = breakdown.get(k, None)

            duration_ms: float | None = None
            if trial.started_at and trial.completed_at:
                duration_ms = round(
                    (trial.completed_at - trial.started_at).total_seconds() * 1000, 2
                )

            summary = TrialComparisonSummary(
                trial_id=trial.id,
                trial_number=trial.trial_number,
                name=trial.name,
                status=trial.status.value,
                configuration=trial.configuration,
                configuration_digest=trial.configuration_digest,
                evaluation_run_id=trial.evaluation_run_id,
                aggregate_score=trial.aggregate_score,
                metric_scores=aligned_scores,
                latency_p50_ms=trial.latency_p50_ms,
                latency_p95_ms=trial.latency_p95_ms,
                latency_p99_ms=trial.latency_p99_ms,
                execution_duration_ms=duration_ms,
                error_summary=trial.error_summary,
            )
            trial_summaries.append(summary)

            if trial.status == TrialStatus.COMPLETED and trial.latency_p50_ms is not None:
                completed_trial_latencies.append((trial.trial_number, trial.latency_p50_ms))

        # 4. Factual Metric Observations (No M9 recommendations or ranking)
        metric_observations: list[MetricObservation] = []
        for key in sorted_metric_keys:
            valid_pairs: list[tuple[int, float]] = []
            for t in trial_summaries:
                val = t.metric_scores.get(key)
                if val is not None:
                    valid_pairs.append((t.trial_number, val))

            if not valid_pairs:
                metric_observations.append(MetricObservation(metric_key=key))
                continue

            scores = [p[1] for p in valid_pairs]
            max_val = max(scores)
            min_val = min(scores)
            mean_val = round(sum(scores) / len(scores), 2)
            highest_trials = [p[0] for p in valid_pairs if p[1] == max_val]

            metric_observations.append(
                MetricObservation(
                    metric_key=key,
                    highest_observed_score=max_val,
                    highest_scoring_trials=highest_trials,
                    lowest_observed_score=min_val,
                    mean_observed_score=mean_val,
                )
            )

        # 5. Factual Latency Observations
        lowest_latency_ms: float | None = None
        lowest_latency_trials: list[int] = []
        if completed_trial_latencies:
            lowest_latency_ms = min(p[1] for p in completed_trial_latencies)
            lowest_latency_trials = [
                p[0] for p in completed_trial_latencies if p[1] == lowest_latency_ms
            ]

        return ExperimentComparisonResponse(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            status=experiment.status.value,
            dataset_version_id=experiment.dataset_version_id,
            evaluation_suite_version_id=experiment.evaluation_suite_version_id or "",
            evaluation_split=experiment.evaluation_split.value,
            total_trials=len(trials),
            completed_trials=experiment.completed_trials,
            failed_trials=experiment.failed_trials,
            trials=trial_summaries,
            metric_keys=sorted_metric_keys,
            metric_observations=metric_observations,
            lowest_observed_latency_ms=lowest_latency_ms,
            lowest_latency_trials=lowest_latency_trials,
            compatibility_verified=is_compatible,
            compatibility_notes=compatibility_notes,
        )
