"""Centralized metadata and effective bit calculations for supported quantization formats."""

from __future__ import annotations

from typing import Any

QUANTIZATION_METADATA: dict[str, dict[str, Any]] = {
    "FP16": {
        "format_key": "FP16",
        "format_family": "FLOAT",
        "nominal_bits": 16.0,
        "effective_reference_bits": 16.0,
        "runtime_requirements": ["pytorch", "ollama", "vllm", "tgi", "onnx"],
        "supported_hardware": ["CPU", "GPU"],
        "calculation_assumptions": (
            "Standard IEEE 754 half-precision: exactly 16 bits (2.0 bytes) per parameter."
        ),
        "limitations": (
            "Highest memory usage among standard deployment formats. Requires substantial RAM/VRAM."
        ),
        "source_reference": "IEEE 754-2008 Standard",
        "registry_version": "1.0.0",
    },
    "Q8_0": {
        "format_key": "Q8_0",
        "format_family": "GGUF",
        "nominal_bits": 8.0,
        "effective_reference_bits": 8.5,
        "runtime_requirements": ["llama.cpp", "ollama"],
        "supported_hardware": ["CPU", "GPU"],
        "calculation_assumptions": (
            "GGUF 8-bit quantization with 32-weight blocks. Effective ~8.5 bits/weight including block scales."
        ),
        "limitations": (
            "Minimal accuracy loss compared to FP16. Moderate memory reduction (~47%)."
        ),
        "source_reference": "GGUF Specification (llama.cpp)",
        "registry_version": "1.0.0",
    },
    "Q4_K_M": {
        "format_key": "Q4_K_M",
        "format_family": "GGUF",
        "nominal_bits": 4.0,
        "effective_reference_bits": 4.9,
        "runtime_requirements": ["llama.cpp", "ollama"],
        "supported_hardware": ["CPU", "GPU"],
        "calculation_assumptions": (
            "k-quantization medium scheme: uses 4.5 to 5.5 bits per layer; average effective reference 4.9 bits/weight."
        ),
        "limitations": (
            "Small perplexity delta on complex reasoning. Excellent efficiency for 8 GB RAM local workstations."
        ),
        "source_reference": "llama.cpp k-quants PR #1684",
        "registry_version": "1.0.0",
    },
    "AWQ": {
        "format_key": "AWQ",
        "format_family": "AWQ",
        "nominal_bits": 4.0,
        "effective_reference_bits": 4.5,
        "runtime_requirements": ["vllm", "tgi", "transformers"],
        "supported_hardware": ["GPU"],
        "calculation_assumptions": (
            "Activation-aware Weight Quantization (Lin et al.) with 128-weight grouping. "
            "Nominal 4-bit weights with scale/zero-point overhead yields ~4.5 bits/weight."
        ),
        "limitations": (
            "Strictly GPU only. Not supported on CPU runtimes or GGUF executors. "
            "Requires CUDA Compute Capability >= 7.5 (Turing or newer, e.g. T4, A100)."
        ),
        "source_reference": "Lin et al., AWQ: Activation-aware Weight Quantization for LLM Compression (2023)",
        "registry_version": "1.0.0",
    },
}


def is_quantization_supported(format_key: str) -> bool:
    """Return True if the quantization format is recognized by the registry."""
    return format_key.upper().strip() in QUANTIZATION_METADATA


def get_quantization_info(format_key: str) -> dict[str, Any]:
    """Retrieve detailed specification for a quantization format or raise ValueError."""
    key = format_key.upper().strip()
    if key not in QUANTIZATION_METADATA:
        raise ValueError(
            f"Unsupported quantization format '{format_key}'. "
            f"Permitted formats: {list(QUANTIZATION_METADATA.keys())}"
        )
    return QUANTIZATION_METADATA[key].copy()


def list_quantization_formats() -> list[dict[str, Any]]:
    """Return list of all registered quantization format specifications."""
    return [v.copy() for v in QUANTIZATION_METADATA.values()]


def calculate_weight_bytes(param_count: float, format_key: str) -> int:
    """Calculate the estimated total raw weight memory in bytes for a given parameter count."""
    info = get_quantization_info(format_key)
    effective_bits = info["effective_reference_bits"]
    return int(round((param_count * effective_bits) / 8.0))


class QuantizationFormatItem:
    """Helper wrapper for format metadata."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.id = data["format_key"]
        self.format_key = data["format_key"]
        self.format_family = data["format_family"]
        self.nominal_bits = float(data["nominal_bits"])
        self.effective_reference_bits = float(data["effective_reference_bits"])
        self.runtime_requirements = list(data.get("runtime_requirements", []))
        self.supported_hardware = list(data.get("supported_hardware", []))
        self.calculation_assumptions = data.get("calculation_assumptions", "")
        self.limitations = data.get("limitations", "")
        self.source_reference = data.get("source_reference", "")
        self.registry_version = data.get("registry_version", "1.0.0")


class QuantizationRegistry:
    """Registry class for querying quantization formats and calculating weight bytes."""

    def list_formats(self) -> list[QuantizationFormatItem]:
        return [QuantizationFormatItem(d) for d in list_quantization_formats()]

    def get_info(self, format_key: str) -> dict[str, Any]:
        return get_quantization_info(format_key)

    def is_supported(self, format_key: str) -> bool:
        return is_quantization_supported(format_key)

    def calculate_weight_bytes(self, param_count: float, format_key: str) -> int:
        return calculate_weight_bytes(param_count, format_key)
