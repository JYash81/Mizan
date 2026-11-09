"""Operational instrumentation helpers for Customer Runtime and Site Agent."""

from __future__ import annotations

from app.modules.observability.metric_registry import metric_registry


def record_runtime_request(
    endpoint: str,
    status_code: int,
    duration_ms: float,
    slot_name: str = "SLOT_A",
    engine: str = "MOCK_ENGINE",
) -> None:
    """Record metrics for an incoming runtime/inference request."""
    status_class = f"{status_code // 100}xx"

    req_labels = {
        "service": "runtime",
        "endpoint": endpoint,
        "status_class": status_class,
        "runtime_engine": engine,
        "slot_name": slot_name,
    }
    metric_registry.record_counter("runtime_requests_total", 1.0, req_labels)

    dur_labels = {
        "service": "runtime",
        "endpoint": endpoint,
        "slot_name": slot_name,
    }
    metric_registry.record_histogram("runtime_request_duration_ms", duration_ms, dur_labels)


def record_inference_tokens(
    prompt_tokens: int,
    completion_tokens: int,
    slot_name: str = "SLOT_A",
) -> None:
    """Record token throughput metrics without recording prompt contents."""
    if prompt_tokens > 0:
        metric_registry.record_counter(
            "runtime_inference_tokens_total",
            float(prompt_tokens),
            {"type": "prompt", "slot_name": slot_name},
        )
    if completion_tokens > 0:
        metric_registry.record_counter(
            "runtime_inference_tokens_total",
            float(completion_tokens),
            {"type": "completion", "slot_name": slot_name},
        )


def record_hardware_snapshot(
    site_id: str,
    cpu_pct: float,
    memory_bytes: float,
    disk_bytes: float,
    vram_bytes: float,
) -> None:
    """Record host and accelerator resource usage metrics."""
    lbl = {"site_id": site_id}
    metric_registry.record_gauge("runtime_cpu_usage_percent", cpu_pct, lbl)
    metric_registry.record_gauge("runtime_memory_allocated_bytes", memory_bytes, lbl)
    metric_registry.record_gauge("runtime_disk_usage_bytes", disk_bytes, lbl)
    metric_registry.record_gauge("runtime_vram_allocated_bytes", vram_bytes, lbl)


def record_slot_state(
    site_id: str,
    slot_name: str,
    readiness: str,
    model_version_id: str,
    engine: str,
    golden_status: str,
) -> None:
    """Record active slot configuration and operational readiness status."""
    metric_registry.record_gauge(
        "runtime_active_slot_info",
        1.0,
        {
            "site_id": site_id,
            "slot_name": slot_name,
            "model_version_id": model_version_id,
            "engine": engine,
        },
    )
    metric_registry.record_gauge(
        "runtime_readiness_state",
        1.0 if readiness == "READY" else 0.0,
        {"site_id": site_id, "slot_name": slot_name},
    )
    metric_registry.record_gauge(
        "runtime_golden_test_status",
        1.0 if golden_status == "PASSED" else 0.0,
        {"site_id": site_id, "slot_name": slot_name},
    )


def record_site_agent_heartbeat(site_id: str, is_alive: bool) -> None:
    """Record Site Agent connectivity status."""
    metric_registry.record_gauge(
        "runtime_site_agent_heartbeat_status",
        1.0 if is_alive else 0.0,
        {"site_id": site_id},
    )
