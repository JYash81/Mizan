"""Optional Preference-Weighted Scoring Engine for Multi-Objective Trade-Offs.

Allows users to rank eligible candidates under explicitly configured preference weights.
Preserves transparency: scores represent preference alignment, NOT universal model quality.
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field

from app.modules.recommendations.objective_registry import ObjectiveRegistry


class WeightedScoreDetail(BaseModel):
    """Detailed calculation breakdown for a single candidate under preference weights."""

    candidate_id: str
    weighted_score: float | None
    rank: int | None = None
    component_contributions: dict[str, float] = Field(default_factory=dict)
    missing_objectives: list[str] = Field(default_factory=list)
    formula_explanation: str


class WeightedScoringResult(BaseModel):
    """Result of evaluating a preference weighting scenario across candidates."""

    scenario_name: str
    weights: dict[str, float]
    ranked_candidates: list[WeightedScoreDetail] = Field(default_factory=list)
    ranking_explanation: str
    algorithm_version: str = "1.0.0"


# Explicit user preference presets with transparent weight distributions
PREFERENCE_PRESETS: dict[str, dict[str, float]] = {
    "QUALITY_FIRST": {
        "aggregate_score": 0.60,
        "latency_p95_ms": 0.20,
        "required_ram_mb": 0.20,
    },
    "LATENCY_SENSITIVE": {
        "latency_p95_ms": 0.50,
        "aggregate_score": 0.30,
        "required_ram_mb": 0.20,
    },
    "RESOURCE_CONSTRAINED": {
        "required_ram_mb": 0.50,
        "aggregate_score": 0.25,
        "latency_p95_ms": 0.25,
    },
    "BALANCED": {
        "aggregate_score": 0.34,
        "latency_p95_ms": 0.33,
        "required_ram_mb": 0.33,
    },
}


class WeightedScoringEngine:
    """Computes preference-weighted scores on normalized candidate vectors."""

    WEIGHT_SUM_TOLERANCE = 0.005

    @classmethod
    def validate_weights(
        cls,
        weights: dict[str, float],
        allowed_objectives: list[str] | None = None,
    ) -> list[str]:
        """Validate preference weights against strict business rules.

        Returns list of validation error messages. Empty list indicates valid weights.
        """
        errors: list[str] = []

        if not weights:
            errors.append("Weights dictionary cannot be empty.")
            return errors

        total_weight = 0.0

        for key, w in weights.items():
            if not isinstance(w, (int, float)):
                errors.append(f"Weight for '{key}' must be a numeric float, got {type(w).__name__}.")
                continue

            if math.isnan(w) or math.isinf(w):
                errors.append(f"Weight for '{key}' cannot be NaN or infinite.")
                continue

            if w < 0.0:
                errors.append(f"Weight for '{key}' must be non-negative (>= 0.0), got {w}.")
                continue

            # Verify key is in registry
            if ObjectiveRegistry.get_objective(key) is None:
                errors.append(f"Unsupported objective key in weights: '{key}'.")

            if allowed_objectives and key not in allowed_objectives:
                errors.append(f"Objective '{key}' is not in the active comparison set.")

            total_weight += float(w)

        if not errors:
            if abs(total_weight - 1.0) > cls.WEIGHT_SUM_TOLERANCE:
                errors.append(
                    f"Weights must sum to 1.0 (100%), but sum to {total_weight:.4f} (tolerance +/- {cls.WEIGHT_SUM_TOLERANCE})."
                )

        return errors

    @classmethod
    def calculate_weighted_scores(
        cls,
        candidates: list[dict[str, Any]],
        weights: dict[str, float],
        scenario_name: str = "User Preference",
        id_field: str = "id",
        normalized_values_field: str = "normalized_objective_values",
        eligibility_field: str = "is_eligible",
    ) -> WeightedScoringResult:
        """Calculate weighted score for eligible candidates.

        Ineligible candidates do not receive a competitive rank.
        """
        validation_errors = cls.validate_weights(weights)
        if validation_errors:
            raise ValueError(f"Invalid preference weights: {'; '.join(validation_errors)}")

        score_details: list[WeightedScoreDetail] = []

        for cand in candidates:
            cid = str(cand[id_field])
            is_eligible = cand.get(eligibility_field, True)
            norm_values = cand.get(normalized_values_field, {})

            if not is_eligible:
                score_details.append(
                    WeightedScoreDetail(
                        candidate_id=cid,
                        weighted_score=None,
                        rank=None,
                        component_contributions={},
                        missing_objectives=[],
                        formula_explanation=f"Candidate {cid} is ineligible due to hard constraint failure.",
                    )
                )
                continue

            total_score = 0.0
            components: dict[str, float] = {}
            missing: list[str] = []

            for obj_key, weight in weights.items():
                norm_val = norm_values.get(obj_key)
                if norm_val is None:
                    missing.append(obj_key)
                else:
                    contribution = round(weight * float(norm_val), 4)
                    components[obj_key] = contribution
                    total_score += contribution

            if missing:
                # Candidate lacks some required weighted objectives
                explanation = (
                    f"Candidate lacks data for: {', '.join(missing)}. "
                    f"Score computed across available objectives."
                )
            else:
                comp_strs = [f"{w:.2f} * {norm_values.get(k, 0.0):.2f}" for k, w in weights.items()]
                explanation = f"Score = {' + '.join(comp_strs)} = {total_score:.4f}"

            score_details.append(
                WeightedScoreDetail(
                    candidate_id=cid,
                    weighted_score=round(total_score, 4),
                    component_contributions=components,
                    missing_objectives=missing,
                    formula_explanation=explanation,
                )
            )

        # Rank eligible candidates deterministically by score (descending), then ID (ascending)
        eligible_scored = [d for d in score_details if d.weighted_score is not None]
        eligible_scored.sort(key=lambda x: (-x.weighted_score, x.candidate_id))

        for rank_idx, item in enumerate(eligible_scored, start=1):
            item.rank = rank_idx

        # Top summary
        top_cand = eligible_scored[0].candidate_id if eligible_scored else "None"
        ranking_summary = (
            f"Evaluated {len(eligible_scored)} eligible candidate(s) under '{scenario_name}' weights. "
            f"Highest-scoring candidate under these preferences: {top_cand}."
        )

        return WeightedScoringResult(
            scenario_name=scenario_name,
            weights=weights,
            ranked_candidates=score_details,
            ranking_explanation=ranking_summary,
        )
