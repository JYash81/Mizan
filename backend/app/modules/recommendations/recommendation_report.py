"""Recommendation Report Generator.

Exports deterministic, auditable multi-objective recommendation reports
in structured JSON, Markdown, and CSV formats.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any


class RecommendationReportService:
    """Generates structured report exports for recommendation runs."""

    @staticmethod
    def generate_json_report(run_data: dict[str, Any]) -> str:
        """Export complete recommendation run snapshot in formatted JSON."""
        return json.dumps(run_data, indent=2, sort_keys=True, default=str)

    @staticmethod
    def generate_markdown_report(run_data: dict[str, Any]) -> str:
        """Export human-readable Markdown recommendation report."""
        lines: list[str] = [
            f"# MIZAN Recommendation Report: {run_data.get('name', 'Untitled Run')}",
            f"**Run ID:** `{run_data.get('id')}`  ",
            f"**Status:** {run_data.get('status')}  ",
            f"**Algorithm Version:** {run_data.get('algorithm_version', '1.0.0')}  ",
            f"**Input Digest (SHA-256):** `{run_data.get('input_digest')}`  ",
            f"**Created At:** {run_data.get('created_at')}  ",
            "\n---\n",
            "## 1. Executive Summary & KPIs\n",
            f"- **Total Candidates Evaluated:** {run_data.get('total_candidates', 0)}",
            f"- **Eligible Candidates:** {run_data.get('eligible_candidates', 0)}",
            f"- **Pareto Frontier Candidates:** {run_data.get('frontier_candidates', 0)}",
            "\n---\n",
            "## 2. Multi-Objective Comparison Matrix\n",
        ]

        candidates = run_data.get("candidates", [])
        if candidates:
            lines.append(
                "| Candidate | Status | Pareto Frontier | Score (pts) | P95 Latency (ms) | RAM (MB) | Cost ($) |"
            )
            lines.append(
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
            )

            for cand in candidates:
                raw_vals = cand.get("objective_values", {})
                score = raw_vals.get("aggregate_score", "-")
                lat = raw_vals.get("latency_p95_ms", "-")
                ram = raw_vals.get("required_ram_mb", "-")
                cost = raw_vals.get("estimated_cost_usd", "-")
                is_front = "YES (Optimal)" if cand.get("pareto_frontier_member") else "No"
                elig = cand.get("eligibility_status", "UNKNOWN")

                lines.append(
                    f"| **{cand.get('candidate_label')}** | {elig} | {is_front} | {score} | {lat} | {ram} | {cost} |"
                )

        lines.extend([
            "\n---\n",
            "## 3. Explanations & Trade-Off Analysis\n",
        ])

        for cand in candidates:
            lines.append(f"### {cand.get('candidate_label')}")
            lines.append(f"- **Eligibility:** {cand.get('eligibility_status')}")
            lines.append(f"- **Pareto Member:** {cand.get('pareto_frontier_member')}")
            if cand.get("exclusion_reasons"):
                lines.append(f"- **Exclusions:** {'; '.join(cand.get('exclusion_reasons'))}")
            lines.append(f"- **Explanation:** {cand.get('explanation_text', 'No explanation provided.')}\n")

        # Scenarios
        scenarios = run_data.get("scenarios", [])
        if scenarios:
            lines.extend([
                "---",
                "## 4. Preference Scenarios & Sensitivity Analysis\n",
            ])
            for s in scenarios:
                lines.append(f"### Scenario: {s.get('scenario_name')}")
                if s.get("explanation"):
                    lines.append(f"- **Summary:** {s.get('explanation')}")
                weights = s.get("weight_snapshot") or {}
                if weights:
                    w_str = ", ".join(f"{k}: {v*100:.1f}%" for k, v in weights.items())
                    lines.append(f"- **Weights:** {w_str}")
                lines.append("")

        # Decisions
        decisions = run_data.get("decisions", [])
        if decisions:
            sec_num = "5" if scenarios else "4"
            lines.extend([
                "---",
                f"## {sec_num}. Human Review & Decision Records\n",
            ])
            for d in decisions:
                lines.append(f"- **Decision:** {d.get('decision')} by `{d.get('actor_id')}` on {d.get('created_at')}")
                lines.append(f"  - **Reason:** {d.get('decision_reason')}")

        notice_num = "6" if scenarios and decisions else ("5" if scenarios or decisions else "4")
        lines.extend([
            "\n---\n",
            f"## {notice_num}. Free-Only Infrastructure Notice\n",
            "All recommendations were computed deterministically using local CPU processing. "
            "Zero additional infrastructure costs ($0.00) were incurred.",
        ])

        return "\n".join(lines)

    @staticmethod
    def generate_csv_report(candidates: list[dict[str, Any]]) -> str:
        """Export candidate matrix in tabular CSV format."""
        output = io.StringIO()
        fieldnames = [
            "candidate_id",
            "candidate_label",
            "eligibility_status",
            "pareto_frontier_member",
            "weighted_score",
            "aggregate_score",
            "latency_p50_ms",
            "latency_p95_ms",
            "execution_duration_ms",
            "required_ram_mb",
            "artifact_size_mb",
            "estimated_cost_usd",
            "configuration_digest",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for cand in candidates:
            raw_vals = cand.get("objective_values", {})
            row = {
                "candidate_id": cand.get("id"),
                "candidate_label": cand.get("candidate_label"),
                "eligibility_status": cand.get("eligibility_status"),
                "pareto_frontier_member": cand.get("pareto_frontier_member"),
                "weighted_score": cand.get("weighted_score"),
                "aggregate_score": raw_vals.get("aggregate_score"),
                "latency_p50_ms": raw_vals.get("latency_p50_ms"),
                "latency_p95_ms": raw_vals.get("latency_p95_ms"),
                "execution_duration_ms": raw_vals.get("execution_duration_ms"),
                "required_ram_mb": raw_vals.get("required_ram_mb"),
                "artifact_size_mb": raw_vals.get("artifact_size_mb"),
                "estimated_cost_usd": raw_vals.get("estimated_cost_usd"),
                "configuration_digest": cand.get("configuration_digest"),
            }
            writer.writerow(row)

        return output.getvalue()
