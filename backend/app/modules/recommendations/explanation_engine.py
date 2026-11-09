"""Deterministic Recommendation Explanation Engine.

Synthesizes fact-based, mathematically grounded natural language explanations
from optimization records, constraint evaluations, and Pareto dominance relationships.
Never calls an external LLM for scoring or explanation generation.
"""

from __future__ import annotations

from typing import Any

from app.models.recommendations import CandidateEligibilityStatus


class ExplanationEngine:
    """Generates transparent, deterministic explanations for recommendation candidates."""

    @classmethod
    def explain_candidate(
        cls,
        candidate_id: str,
        label: str,
        eligibility_status: CandidateEligibilityStatus,
        exclusion_reasons: list[str],
        is_frontier_member: bool,
        dominating_ids: list[str],
        dominated_ids: list[str],
        raw_values: dict[str, Any],
        evidence_summary: dict[str, str],
        all_candidates_map: dict[str, dict[str, Any]] | None = None,
    ) -> str:
        """Generate a complete, fact-checked explanation for a candidate."""
        parts: list[str] = []

        # 1. Ineligible candidate explanation
        if eligibility_status != CandidateEligibilityStatus.ELIGIBLE:
            parts.append(
                f"Candidate '{label}' is classified as {eligibility_status.value}."
            )
            if exclusion_reasons:
                parts.append("Hard constraint failure reasons: " + "; ".join(exclusion_reasons))
            return " ".join(parts)

        # 2. Pareto Frontier Member explanation
        if is_frontier_member:
            parts.append(
                f"Candidate '{label}' is a non-dominated Pareto frontier member under the evaluated objectives."
            )

            # Highlight notable strengths
            strengths: list[str] = []
            agg_score = raw_values.get("aggregate_score")
            if agg_score is not None:
                strengths.append(f"Aggregate Quality: {float(agg_score):.1f} pts")

            lat_p95 = raw_values.get("latency_p95_ms")
            if lat_p95 is not None:
                strengths.append(f"P95 Latency: {float(lat_p95):.1f} ms")

            ram = raw_values.get("required_ram_mb")
            if ram is not None:
                strengths.append(f"Estimated RAM: {float(ram):.0f} MB")

            cost = raw_values.get("estimated_cost_usd")
            if cost is not None:
                strengths.append(f"Estimated Cost: ${cost}")

            if strengths:
                parts.append("Observed profile: " + ", ".join(strengths) + ".")

            if dominated_ids:
                count = len(dominated_ids)
                parts.append(f"It strictly dominates {count} other candidate(s).")
            else:
                parts.append(
                    "While it does not strictly dominate other candidates, no other eligible candidate outperforms it across all selected objectives."
                )

        # 3. Dominated candidate explanation
        else:
            parts.append(
                f"Candidate '{label}' is not on the Pareto frontier because it is strictly dominated by other eligible configuration(s)."
            )
            if dominating_ids:
                dom_names: list[str] = []
                for did in dominating_ids[:3]:
                    c_info = (all_candidates_map or {}).get(did, {})
                    c_label = c_info.get("candidate_label", did)
                    dom_names.append(f"'{c_label}'")
                parts.append(f"Strictly outperformed across comparable objectives by: {', '.join(dom_names)}.")

        # 4. Evidence Provenance annotations
        missing_or_est: list[str] = []
        for obj_key, ev_type in evidence_summary.items():
            if ev_type in ("UNAVAILABLE", "UNKNOWN", "ESTIMATED"):
                missing_or_est.append(f"{obj_key} ({ev_type})")

        if missing_or_est:
            parts.append("Evidence notice: " + ", ".join(missing_or_est) + ".")

        return " ".join(parts)
