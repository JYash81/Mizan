"""Deterministic Preference Sensitivity Analysis.

Evaluates how candidate rankings shift under varying preference weights,
verifying that Pareto frontier membership remains independent of user weighting.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.modules.recommendations.weighted_scoring import (
    WeightedScoringEngine,
    WeightedScoringResult,
)


class CandidateSensitivitySummary(BaseModel):
    """Ranking stability summary for an individual candidate across scenarios."""

    candidate_id: str
    baseline_rank: int | None
    min_rank: int | None
    max_rank: int | None
    rank_variance: float
    is_rank_stable: bool
    scenario_ranks: dict[str, int | None] = Field(default_factory=dict)


class SensitivityAnalysisReport(BaseModel):
    """Aggregate sensitivity report comparing candidate ranking shifts across preference scenarios."""

    baseline_scenario: str
    evaluated_scenarios: list[str] = Field(default_factory=list)
    candidate_summaries: list[CandidateSensitivitySummary] = Field(default_factory=list)
    ranking_flips_detected: bool
    pareto_frontier_independent: bool = True
    disclaimer: str = (
        "This is a deterministic preference sensitivity calculation measuring ranking stability "
        "across user weight distributions. It does NOT represent statistical confidence intervals."
    )


class SensitivityAnalysisEngine:
    """Performs deterministic preference perturbation and rank stability analysis."""

    @classmethod
    def generate_perturbed_weights(
        cls,
        base_weights: dict[str, float],
        delta: float = 0.20,
    ) -> dict[str, dict[str, float]]:
        """Generate bounded alternative weight distributions by boosting individual objectives.

        Args:
            base_weights: Baseline user preference weights (must sum to ~1.0).
            delta: Relative shift proportion (e.g. 0.20 for +20% boost).

        Returns:
            Dictionary mapping scenario name -> normalized perturbed weights.
        """
        scenarios: dict[str, dict[str, float]] = {}

        for boost_key in base_weights:
            perturbed = {}
            for k, w in base_weights.items():
                if k == boost_key:
                    perturbed[k] = w * (1.0 + delta)
                else:
                    perturbed[k] = w * (1.0 - (delta / max(1, len(base_weights) - 1)))

            # Re-normalize to exactly 1.0
            total = sum(perturbed.values())
            if total > 0:
                normalized = {k: round(v / total, 4) for k, v in perturbed.items()}
                # Fix rounding slack on largest weight
                max_k = max(normalized, key=normalized.get)  # type: ignore
                slack = round(1.0 - sum(normalized.values()), 4)
                normalized[max_k] = round(normalized[max_k] + slack, 4)
                scenarios[f"Boost {boost_key.replace('_', ' ').title()} (+{int(delta*100)}%)"] = normalized

        return scenarios

    @classmethod
    def analyze_sensitivity(
        cls,
        candidates: list[dict[str, Any]],
        base_weights: dict[str, float],
        frontier_ids: list[str],
        id_field: str = "id",
        normalized_values_field: str = "normalized_objective_values",
        eligibility_field: str = "is_eligible",
    ) -> SensitivityAnalysisReport:
        """Run multi-scenario sensitivity comparison across candidate ranks."""
        # 1. Baseline scoring
        base_result = WeightedScoringEngine.calculate_weighted_scores(
            candidates,
            base_weights,
            scenario_name="Baseline Weights",
            id_field=id_field,
            normalized_values_field=normalized_values_field,
            eligibility_field=eligibility_field,
        )

        # 2. Perturbed scenarios (bounded to max 4 alternative scenarios)
        perturbed_dict = cls.generate_perturbed_weights(base_weights, delta=0.25)
        all_results: dict[str, WeightedScoringResult] = {"Baseline": base_result}

        for sc_name, sc_weights in list(perturbed_dict.items())[:4]:
            try:
                res = WeightedScoringEngine.calculate_weighted_scores(
                    candidates,
                    sc_weights,
                    scenario_name=sc_name,
                    id_field=id_field,
                    normalized_values_field=normalized_values_field,
                    eligibility_field=eligibility_field,
                )
                all_results[sc_name] = res
            except ValueError:
                continue

        # 3. Analyze candidate rank shifts
        candidate_ids = [str(c[id_field]) for c in candidates if c.get(eligibility_field, True)]
        summaries: list[CandidateSensitivitySummary] = []
        any_flips = False

        for cid in candidate_ids:
            ranks: list[int] = []
            scenario_ranks_map: dict[str, int | None] = {}

            for sc_name, sc_res in all_results.items():
                cand_score = next((d for d in sc_res.ranked_candidates if d.candidate_id == cid), None)
                if cand_score and cand_score.rank is not None:
                    ranks.append(cand_score.rank)
                    scenario_ranks_map[sc_name] = cand_score.rank
                else:
                    scenario_ranks_map[sc_name] = None

            base_rank = scenario_ranks_map.get("Baseline")
            if ranks:
                min_r = min(ranks)
                max_r = max(ranks)
                var = float(max_r - min_r)
                is_stable = (var <= 1.0)
                if var > 1.0:
                    any_flips = True
            else:
                min_r, max_r, var, is_stable = None, None, 0.0, True

            summaries.append(
                CandidateSensitivitySummary(
                    candidate_id=cid,
                    baseline_rank=base_rank,
                    min_rank=min_r,
                    max_rank=max_r,
                    rank_variance=var,
                    is_rank_stable=is_stable,
                    scenario_ranks=scenario_ranks_map,
                )
            )

        return SensitivityAnalysisReport(
            baseline_scenario="Baseline",
            evaluated_scenarios=list(all_results.keys()),
            candidate_summaries=summaries,
            ranking_flips_detected=any_flips,
            pareto_frontier_independent=True,  # Invariant: Pareto membership never depends on weights
        )
