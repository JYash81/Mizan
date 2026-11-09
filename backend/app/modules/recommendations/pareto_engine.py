"""Mathematically rigorous Pareto Dominance and Frontier Engine.

Evaluates multi-objective trade-offs and identifies the non-dominated Pareto frontier.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParetoDominanceResult(BaseModel):
    """Result of multi-objective Pareto analysis across candidates."""

    frontier_candidate_ids: list[str] = Field(default_factory=list)
    dominated_by: dict[str, list[str]] = Field(default_factory=dict)  # cand_id -> [dominating_cand_ids]
    dominates: dict[str, list[str]] = Field(default_factory=dict)     # cand_id -> [dominated_cand_ids]
    incomparable_pairs: list[tuple[str, str]] = Field(default_factory=list)
    evaluation_notes: list[str] = Field(default_factory=list)


class ParetoEngine:
    """Computes Pareto dominance and identifies the optimal frontier."""

    TOLERANCE = 1e-6  # Floating point comparison tolerance

    @classmethod
    def check_dominance(
        cls,
        vec_a: dict[str, float | None],
        vec_b: dict[str, float | None],
        objective_keys: list[str],
    ) -> bool:
        """Test whether vector A strictly dominates vector B.

        Returns True iff:
        - A is at least as good as B on every comparable objective (A_i >= B_i - eps)
        - A is strictly better than B on at least one objective (A_j > B_j + eps)
        - Both vectors have valid (non-None) data for all evaluated objectives.
        """
        strictly_better_count = 0

        for key in objective_keys:
            val_a = vec_a.get(key)
            val_b = vec_b.get(key)

            # Strict Missing Data Invariant: If either candidate lacks data, dominance cannot be declared
            if val_a is None or val_b is None:
                return False

            if val_a < (val_b - cls.TOLERANCE):
                # A is strictly worse on this objective -> A cannot dominate B
                return False

            if val_a > (val_b + cls.TOLERANCE):
                strictly_better_count += 1

        return strictly_better_count > 0

    @classmethod
    def compute_frontier(
        cls,
        candidates: list[dict[str, Any]],
        objective_keys: list[str],
        id_field: str = "id",
        eligibility_field: str = "is_eligible",
        normalized_values_field: str = "normalized_objective_values",
    ) -> ParetoDominanceResult:
        """Compute the Pareto frontier and dominance relationships across candidates.

        Args:
            candidates: List of candidate dictionaries.
            objective_keys: List of objective keys being evaluated.
            id_field: Key for unique candidate identifier.
            eligibility_field: Boolean key indicating if candidate passed hard constraints.
            normalized_values_field: Key containing dict of normalized objective values.

        Returns:
            ParetoDominanceResult with frontier IDs and dominance graph.
        """
        result = ParetoDominanceResult()

        # Separate eligible candidates from ineligible
        eligible_candidates: list[dict[str, Any]] = []
        for cand in candidates:
            cid = str(cand[id_field])
            result.dominated_by[cid] = []
            result.dominates[cid] = []

            # Ineligible candidates cannot participate in the frontier
            if cand.get(eligibility_field, True):
                eligible_candidates.append(cand)
            else:
                result.evaluation_notes.append(
                    f"Candidate {cid} excluded from Pareto analysis due to hard constraint failure."
                )

        if not eligible_candidates:
            result.evaluation_notes.append("No eligible candidates available for Pareto analysis.")
            return result

        n = len(eligible_candidates)

        # Pairwise comparison across all eligible candidates
        for i in range(n):
            cand_a = eligible_candidates[i]
            id_a = str(cand_a[id_field])
            vec_a = cand_a.get(normalized_values_field, {})

            for j in range(i + 1, n):
                cand_b = eligible_candidates[j]
                id_b = str(cand_b[id_field])
                vec_b = cand_b.get(normalized_values_field, {})

                a_dominates_b = cls.check_dominance(vec_a, vec_b, objective_keys)
                b_dominates_a = cls.check_dominance(vec_b, vec_a, objective_keys)

                if a_dominates_b:
                    result.dominates[id_a].append(id_b)
                    result.dominated_by[id_b].append(id_a)
                elif b_dominates_a:
                    result.dominates[id_b].append(id_a)
                    result.dominated_by[id_a].append(id_b)
                else:
                    result.incomparable_pairs.append((id_a, id_b))

        # Frontier members are eligible candidates that are not dominated by anyone
        frontier: list[str] = []
        for cand in eligible_candidates:
            cid = str(cand[id_field])
            if len(result.dominated_by[cid]) == 0:
                frontier.append(cid)

        # Deterministic sorting of frontier IDs for reproducibility
        result.frontier_candidate_ids = sorted(frontier)

        return result
