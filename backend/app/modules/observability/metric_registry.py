"""Centralized Metric Registry, thread-safe memory storage, and cardinality budgeting for M14."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from app.models.observability import MetricType
from app.modules.observability.telemetry_privacy import validate_and_sanitize_labels

# Default histogram bucket bounds in milliseconds
DEFAULT_HISTOGRAM_BUCKETS = [10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0]
MAX_LABEL_SERIES_PER_METRIC = 50


@dataclass
class MetricMeta:
    key: str
    name: str
    description: str
    metric_type: MetricType
    unit: str
    allowed_labels: list[str]


# Catalog of registered metrics with low-cardinality allowlisted dimensions
STANDARD_METRIC_CATALOG: dict[str, MetricMeta] = {
    "runtime_requests_total": MetricMeta(
        key="runtime_requests_total",
        name="Runtime Requests Total",
        description="Total number of HTTP inference and runtime requests served.",
        metric_type=MetricType.COUNTER,
        unit="requests",
        allowed_labels=["service", "endpoint", "status_class", "runtime_engine", "slot_name"],
    ),
    "runtime_request_duration_ms": MetricMeta(
        key="runtime_request_duration_ms",
        name="Runtime Request Duration",
        description="Latency histogram of runtime requests in milliseconds.",
        metric_type=MetricType.HISTOGRAM,
        unit="ms",
        allowed_labels=["service", "endpoint", "slot_name"],
    ),
    "runtime_active_slot_info": MetricMeta(
        key="runtime_active_slot_info",
        name="Runtime Active Slot Information",
        description="Information gauge for the currently active Blue/Green slot.",
        metric_type=MetricType.GAUGE,
        unit="info",
        allowed_labels=["site_id", "slot_name", "model_version_id", "engine"],
    ),
    "runtime_readiness_state": MetricMeta(
        key="runtime_readiness_state",
        name="Runtime Readiness State",
        description="Boolean gauge indicating whether the active slot is ready (1) or unready (0).",
        metric_type=MetricType.GAUGE,
        unit="state",
        allowed_labels=["site_id", "slot_name"],
    ),
    "runtime_inference_tokens_total": MetricMeta(
        key="runtime_inference_tokens_total",
        name="Runtime Inference Tokens Total",
        description="Cumulative prompt and completion tokens processed by the local model.",
        metric_type=MetricType.COUNTER,
        unit="tokens",
        allowed_labels=["type", "slot_name"],
    ),
    "runtime_cpu_usage_percent": MetricMeta(
        key="runtime_cpu_usage_percent",
        name="Runtime CPU Usage Percent",
        description="Percentage of host CPU utilized by customer runtime.",
        metric_type=MetricType.GAUGE,
        unit="percent",
        allowed_labels=["site_id"],
    ),
    "runtime_memory_allocated_bytes": MetricMeta(
        key="runtime_memory_allocated_bytes",
        name="Runtime Memory Allocated Bytes",
        description="Bytes of system RAM allocated by customer runtime.",
        metric_type=MetricType.GAUGE,
        unit="bytes",
        allowed_labels=["site_id"],
    ),
    "runtime_disk_usage_bytes": MetricMeta(
        key="runtime_disk_usage_bytes",
        name="Runtime Disk Usage Bytes",
        description="Bytes of disk storage consumed by local model artifacts.",
        metric_type=MetricType.GAUGE,
        unit="bytes",
        allowed_labels=["site_id"],
    ),
    "runtime_vram_allocated_bytes": MetricMeta(
        key="runtime_vram_allocated_bytes",
        name="Runtime VRAM Allocated Bytes",
        description="Bytes of GPU VRAM allocated for model weights and KV cache.",
        metric_type=MetricType.GAUGE,
        unit="bytes",
        allowed_labels=["site_id"],
    ),
    "runtime_golden_test_status": MetricMeta(
        key="runtime_golden_test_status",
        name="Runtime Golden Test Status",
        description="Latest outcome of the golden test suite (1 for PASSED, 0 for FAILED/NOT_RUN).",
        metric_type=MetricType.GAUGE,
        unit="status",
        allowed_labels=["site_id", "slot_name"],
    ),
    "runtime_alerts_active": MetricMeta(
        key="runtime_alerts_active",
        name="Active Alerts Count",
        description="Count of currently firing alerts on the site.",
        metric_type=MetricType.GAUGE,
        unit="alerts",
        allowed_labels=["site_id", "severity"],
    ),
    "runtime_slo_error_budget_percent": MetricMeta(
        key="runtime_slo_error_budget_percent",
        name="SLO Error Budget Remaining Percent",
        description="Percentage of remaining error budget for the active SLO.",
        metric_type=MetricType.GAUGE,
        unit="percent",
        allowed_labels=["slo_id", "workspace_id"],
    ),
    "runtime_site_agent_heartbeat_status": MetricMeta(
        key="runtime_site_agent_heartbeat_status",
        name="Site Agent Heartbeat Status",
        description="1 if Site Agent heartbeat is within active threshold, 0 otherwise.",
        metric_type=MetricType.GAUGE,
        unit="status",
        allowed_labels=["site_id"],
    ),
}


@dataclass
class HistogramSeries:
    buckets: list[float]
    bucket_counts: dict[float, int] = field(default_factory=dict)
    count: int = 0
    total_sum: float = 0.0

    def observe(self, val: float) -> None:
        self.count += 1
        self.total_sum += val
        for b in self.buckets:
            if val <= b:
                self.bucket_counts[b] = self.bucket_counts.get(b, 0) + 1


class MetricRegistry:
    """Thread-safe in-memory metric store for real-time aggregation and Prometheus exposition."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[str, float]] = {}
        self._gauges: dict[str, dict[str, float]] = {}
        self._histograms: dict[str, dict[str, HistogramSeries]] = {}
        self._last_updated: dict[str, float] = {}

    def _format_label_key(self, labels: dict[str, str]) -> str:
        items = sorted(labels.items())
        return ",".join(f'{k}="{v}"' for k, v in items)

    def record_counter(self, metric_key: str, increment: float = 1.0, labels: dict[str, str] | None = None) -> None:
        meta = STANDARD_METRIC_CATALOG.get(metric_key)
        allowed = meta.allowed_labels if meta else []
        clean_labels = validate_and_sanitize_labels(metric_key, labels or {}, allowed)
        l_key = self._format_label_key(clean_labels)

        with self._lock:
            series_map = self._counters.setdefault(metric_key, {})
            if l_key not in series_map and len(series_map) >= MAX_LABEL_SERIES_PER_METRIC:
                l_key = 'overflow="cardinality_limit"'
            series_map[l_key] = series_map.get(l_key, 0.0) + increment
            self._last_updated[metric_key] = time.time()

    def record_gauge(self, metric_key: str, value: float, labels: dict[str, str] | None = None) -> None:
        meta = STANDARD_METRIC_CATALOG.get(metric_key)
        allowed = meta.allowed_labels if meta else []
        clean_labels = validate_and_sanitize_labels(metric_key, labels or {}, allowed)
        l_key = self._format_label_key(clean_labels)

        with self._lock:
            series_map = self._gauges.setdefault(metric_key, {})
            if l_key not in series_map and len(series_map) >= MAX_LABEL_SERIES_PER_METRIC:
                l_key = 'overflow="cardinality_limit"'
            series_map[l_key] = float(value)
            self._last_updated[metric_key] = time.time()

    def record_histogram(
        self,
        metric_key: str,
        value: float,
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ) -> None:
        meta = STANDARD_METRIC_CATALOG.get(metric_key)
        allowed = meta.allowed_labels if meta else []
        clean_labels = validate_and_sanitize_labels(metric_key, labels or {}, allowed)
        l_key = self._format_label_key(clean_labels)
        b_list = buckets or DEFAULT_HISTOGRAM_BUCKETS

        with self._lock:
            series_map = self._histograms.setdefault(metric_key, {})
            if l_key not in series_map:
                if len(series_map) >= MAX_LABEL_SERIES_PER_METRIC:
                    l_key = 'overflow="cardinality_limit"'
                if l_key not in series_map:
                    series_map[l_key] = HistogramSeries(buckets=b_list)
            series_map[l_key].observe(value)
            self._last_updated[metric_key] = time.time()

    def get_counter_value(self, metric_key: str, labels: dict[str, str] | None = None) -> float:
        l_key = self._format_label_key(labels or {})
        with self._lock:
            series = self._counters.get(metric_key, {})
            if not labels:
                return sum(series.values())
            return series.get(l_key, 0.0)

    def get_gauge_value(self, metric_key: str, labels: dict[str, str] | None = None) -> float | None:
        l_key = self._format_label_key(labels or {})
        with self._lock:
            series = self._gauges.get(metric_key, {})
            if not labels and series:
                # Return last or average if no specific label requested
                vals = list(series.values())
                return vals[-1] if vals else None
            return series.get(l_key)

    def get_histogram_snapshot(self, metric_key: str) -> dict[str, HistogramSeries]:
        with self._lock:
            return dict(self._histograms.get(metric_key, {}))

    def get_all_snapshots(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": {k: dict(v) for k, v in self._counters.items()},
                "gauges": {k: dict(v) for k, v in self._gauges.items()},
                "histograms": {k: dict(v) for k, v in self._histograms.items()},
                "last_updated": dict(self._last_updated),
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._last_updated.clear()


# Global in-process registry singleton
metric_registry = MetricRegistry()
