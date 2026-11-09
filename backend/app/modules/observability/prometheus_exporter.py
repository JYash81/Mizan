"""Prometheus text exposition format generator for Milestone 14."""

from __future__ import annotations

from app.modules.observability.metric_registry import (
    STANDARD_METRIC_CATALOG,
    metric_registry,
)


def export_prometheus_metrics() -> str:
    """Generate Prometheus 0.0.4 text format representation of current metrics."""
    lines: list[str] = []
    snapshots = metric_registry.get_all_snapshots()

    counters = snapshots["counters"]
    gauges = snapshots["gauges"]
    histograms = snapshots["histograms"]

    # Export Counters
    for m_key, series_map in counters.items():
        meta = STANDARD_METRIC_CATALOG.get(m_key)
        desc = meta.description if meta else f"{m_key} counter"
        lines.append(f"# HELP {m_key} {desc}")
        lines.append(f"# TYPE {m_key} counter")

        if not series_map:
            lines.append(f"{m_key} 0")
        else:
            for l_str, val in series_map.items():
                lbl = f"{{{l_str}}}" if l_str else ""
                lines.append(f"{m_key}{lbl} {val}")

    # Export Gauges
    for m_key, series_map in gauges.items():
        meta = STANDARD_METRIC_CATALOG.get(m_key)
        desc = meta.description if meta else f"{m_key} gauge"
        lines.append(f"# HELP {m_key} {desc}")
        lines.append(f"# TYPE {m_key} gauge")

        if not series_map:
            lines.append(f"{m_key} 0")
        else:
            for l_str, val in series_map.items():
                lbl = f"{{{l_str}}}" if l_str else ""
                lines.append(f"{m_key}{lbl} {val}")

    # Export Histograms
    for m_key, series_map in histograms.items():
        meta = STANDARD_METRIC_CATALOG.get(m_key)
        desc = meta.description if meta else f"{m_key} histogram"
        lines.append(f"# HELP {m_key} {desc}")
        lines.append(f"# TYPE {m_key} histogram")

        for l_str, hist in series_map.items():
            base_lbl = f"{l_str}," if l_str else ""

            running_count = 0
            for b in hist.buckets:
                running_count += hist.bucket_counts.get(b, 0)
                lines.append(f'{m_key}_bucket{{{base_lbl}le="{b}"}} {running_count}')
            lines.append(f'{m_key}_bucket{{{base_lbl}le="+Inf"}} {hist.count}')
            lines.append(f"{m_key}_sum{{{l_str}}} {round(hist.total_sum, 4)}")
            lines.append(f"{m_key}_count{{{l_str}}} {hist.count}")

    # Ensure trailing newline for Prometheus scrape parser
    return "\n".join(lines) + "\n"
