"""Experiment Report Service for exporting multi-trial comparison data.

Formats supported:
- JSON: Fully structured programmatic export.
- Markdown: Human-readable structured audit table with factual observations.
- CSV: Tabular export for spreadsheet analysis.
"""

from __future__ import annotations

import csv
import io

from app.modules.experiments.schemas.comparison import ExperimentComparisonResponse


class ExperimentReportService:
    @staticmethod
    def export_json(comparison: ExperimentComparisonResponse) -> str:
        """Export comparison data as indented JSON string."""
        return comparison.model_dump_json(indent=2)

    @staticmethod
    def export_markdown(comparison: ExperimentComparisonResponse) -> str:
        """Export comparison data as a formatted Markdown report."""
        lines: list[str] = []
        lines.append(f"# Experiment Report: {comparison.experiment_name}")
        lines.append("")
        lines.append("## Provenance & Metadata")
        lines.append(f"- **Experiment ID**: `{comparison.experiment_id}`")
        lines.append(f"- **Status**: `{comparison.status}`")
        lines.append(f"- **Dataset Version ID**: `{comparison.dataset_version_id}`")
        lines.append(
            f"- **Evaluation Suite Version ID**: `{comparison.evaluation_suite_version_id}`"
        )
        lines.append(f"- **Evaluation Split**: `{comparison.evaluation_split}`")
        lines.append(f"- **Total Trials**: {comparison.total_trials}")
        lines.append(f"- **Completed Trials**: {comparison.completed_trials}")
        lines.append(f"- **Failed Trials**: {comparison.failed_trials}")
        lines.append(
            f"- **Provenance Consistent**: {'Yes' if comparison.compatibility_verified else 'No'}"
        )
        lines.append("")

        # Trial Configurations & Summary Table
        lines.append("## Trial Configurations & Aggregate Results")
        lines.append(
            "| Trial # | Name | Status | Provider | Model | Chunk Size | Overlap | Top K | Aggregate Score | p50 Latency (ms) |"
        )
        lines.append(
            "|---------|------|--------|----------|-------|------------|---------|-------|-----------------|------------------|"
        )

        for t in comparison.trials:
            c = t.configuration
            score_str = f"{t.aggregate_score:.1f}%" if t.aggregate_score is not None else "N/A"
            lat_str = f"{t.latency_p50_ms:.1f}" if t.latency_p50_ms is not None else "N/A"
            lines.append(
                f"| {t.trial_number} | {t.name} | {t.status} | {c.get('provider_name', 'N/A')} | "
                f"{c.get('model_name', 'N/A')} | {c.get('chunk_size', 'N/A')} | "
                f"{c.get('chunk_overlap', 'N/A')} | {c.get('top_k', 'N/A')} | {score_str} | {lat_str} |"
            )
        lines.append("")

        # Metric Scores Alignment Table
        if comparison.metric_keys:
            lines.append("## Aligned Metric Scores")
            header = "| Metric | " + " | ".join(f"Trial {t.trial_number}" for t in comparison.trials) + " |"
            separator = "|--------|" + "|".join("-------" for _ in comparison.trials) + "|"
            lines.append(header)
            lines.append(separator)

            for m_key in comparison.metric_keys:
                row = [f"**{m_key}**"]
                for t in comparison.trials:
                    val = t.metric_scores.get(m_key)
                    row.append(f"{val:.1f}%" if val is not None else "—")
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")

        # Factual Observations
        lines.append("## Factual Observations (Milestone 7 Scope)")
        if comparison.metric_observations:
            for obs in comparison.metric_observations:
                if obs.highest_observed_score is not None:
                    trials_str = ", ".join(f"Trial {t}" for t in obs.highest_scoring_trials)
                    lines.append(
                        f"- **{obs.metric_key}**: Highest observed score was **{obs.highest_observed_score:.1f}%** ({trials_str}); lowest was {obs.lowest_observed_score:.1f}% (mean: {obs.mean_observed_score:.1f}%)."
                    )
        if comparison.lowest_observed_latency_ms is not None:
            trials_lat = ", ".join(f"Trial {t}" for t in comparison.lowest_latency_trials)
            lines.append(
                f"- **Latency**: Lowest observed p50 latency was **{comparison.lowest_observed_latency_ms:.1f} ms** ({trials_lat})."
            )
        lines.append("")
        lines.append(
            "> *Note: Mizan Milestone 7 reports strictly observed factual measurements. No automated ranking, optimal weighting, or model recommendation is performed without explicit human review.*"
        )
        return "\n".join(lines)

    @staticmethod
    def export_csv(comparison: ExperimentComparisonResponse) -> str:
        """Export trial results as tabular CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header columns
        headers = [
            "trial_number",
            "trial_name",
            "status",
            "provider_name",
            "model_name",
            "chunk_size",
            "chunk_overlap",
            "top_k",
            "score_threshold",
            "aggregate_score",
            "latency_p50_ms",
            "latency_p95_ms",
            "execution_duration_ms",
        ]
        for m_key in comparison.metric_keys:
            headers.append(f"metric_{m_key}")

        writer.writerow(headers)

        for t in comparison.trials:
            c = t.configuration
            row = [
                t.trial_number,
                t.name,
                t.status,
                c.get("provider_name", ""),
                c.get("model_name", ""),
                c.get("chunk_size", ""),
                c.get("chunk_overlap", ""),
                c.get("top_k", ""),
                c.get("score_threshold", ""),
                t.aggregate_score if t.aggregate_score is not None else "",
                t.latency_p50_ms if t.latency_p50_ms is not None else "",
                t.latency_p95_ms if t.latency_p95_ms is not None else "",
                t.execution_duration_ms if t.execution_duration_ms is not None else "",
            ]
            for m_key in comparison.metric_keys:
                val = t.metric_scores.get(m_key)
                row.append(val if val is not None else "")
            writer.writerow(row)

        return output.getvalue()
