"""Safe, opt-in, bounded local CPU benchmark service for Mizan."""

from __future__ import annotations

import gc
import logging
import random
import time
from datetime import UTC, datetime
from typing import Any

from app.models.hardware import EvidenceType
from app.modules.hardware.hardware_detection import detect_memory_mb

logger = logging.getLogger(__name__)


class BenchmarkTimeoutError(Exception):
    """Raised when benchmark execution exceeds the safe deadline."""


def run_bounded_cpu_benchmark(matrix_size: int = 300, iterations: int = 5) -> dict[str, Any]:
    """Execute a safe, bounded matrix arithmetic workload on CPU with memory cleanup.

    Invariants:
    - Bounded execution (matrix_size clamped 50..500, iterations 1..10)
    - Memory tracked before and after, explicitly freed via gc.collect()
    - Zero paid services, zero GPU or cloud dependencies
    """
    matrix_size = max(50, min(matrix_size, 500))
    iterations = max(1, min(iterations, 10))

    ram_before, _ = detect_memory_mb()
    started_at = datetime.now(UTC)
    t0 = time.perf_counter()

    # Pre-allocate random 2D matrix
    rng = random.Random(42)
    a = [[rng.random() for _ in range(matrix_size)] for _ in range(matrix_size)]
    b = [[rng.random() for _ in range(matrix_size)] for _ in range(matrix_size)]

    total_ops = 0
    max_duration_seconds = 5.0

    try:
        for _ in range(iterations):
            # Transpose b for cache-friendly dot products
            b_trans = list(zip(*b))
            res = [
                [
                    sum(a[i][k] * b_trans[j][k] for k in range(matrix_size))
                    for j in range(matrix_size)
                ]
                for i in range(matrix_size)
            ]
            total_ops += 2 * (matrix_size**3)
            # Check deadline after each iteration
            if (time.perf_counter() - t0) > max_duration_seconds:
                raise BenchmarkTimeoutError("Benchmark exceeded 5.0s safety execution deadline.")
            # Clear intermediate result
            del res

    except BenchmarkTimeoutError:
        status = "TIMEOUT"
    except Exception as exc:
        logger.error("Benchmark error: %s", exc)
        status = "FAILED"
    else:
        status = "COMPLETED"
    finally:
        # Explicit garbage collection to prevent memory leaks on 8 GB RAM systems
        del a, b
        gc.collect()

    t1 = time.perf_counter()
    completed_at = datetime.now(UTC)
    duration_ms = max(0.1, (t1 - t0) * 1000.0)
    ops_per_second = (total_ops / (duration_ms / 1000.0)) if status == "COMPLETED" else 0.0

    ram_after, _ = detect_memory_mb()

    limitations = (
        "Synthetic CPU float arithmetic test only. Measures single/multi-thread CPU scalar throughput. "
        "Does not measure GPU Tensor Core FLOPS, memory bus bandwidth, or quantized integer matrix operations."
    )

    return {
        "benchmark_name": "Mizan Safe CPU Bounded Matrix Benchmark",
        "benchmark_version": "1.0.0",
        "workload_params_json": f'{{"matrix_size": {matrix_size}, "iterations": {iterations}}}',
        "duration_ms": round(duration_ms, 2),
        "operations_per_second": round(ops_per_second, 2),
        "ram_before_mb": ram_before,
        "ram_after_mb": ram_after,
        "evidence_type": EvidenceType.MEASURED,
        "status": status,
        "limitations": limitations,
        "started_at": started_at,
        "completed_at": completed_at,
    }


class SafeBenchmarkService:
    """Service wrapper for executing bounded CPU benchmarks."""

    def run_cpu_benchmark(self, matrix_size: int = 300, iterations: int = 5) -> dict[str, Any]:
        return run_bounded_cpu_benchmark(matrix_size=matrix_size, iterations=iterations)
