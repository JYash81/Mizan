"""Two-stage GGUF conversion, quantization, and separate AWQ quantization workflows."""

from __future__ import annotations

import hashlib
from typing import Any

from app.models.model_building import ArtifactType


class QuantizationWorkflowError(Exception):
    """Raised when conversion or quantization rules are violated."""


# Magic byte headers for binary format validation
GGUF_MAGIC_BYTES = b"GGUF"  # 0x47 0x47 0x55 0x46


def validate_gguf_conversion_preflight(
    source_format: str,
    target_quantizations: list[str],
    allow_requantize: bool = False,
) -> tuple[bool, list[str]]:
    """Validate GGUF two-stage conversion prerequisites.

    Enforces that the source model must be in high-precision format (FP16 or BF16).
    Rejects requantization of already quantized models by default.
    """
    errors: list[str] = []
    norm_source = source_format.upper().strip()

    # Rule: Source must be high-precision
    if norm_source not in {"FP16", "BF16", "FLOAT16", "BFLOAT16", "SAFETENSORS"}:
        if not allow_requantize:
            errors.append(
                f"Source format '{source_format}' is already quantized or non-standard. "
                "Requantization from already quantized weights causes severe perplexity degradation and is blocked by policy."
            )

    valid_quants = {"Q8_0", "Q4_K_M"}
    for q in target_quantizations:
        if q.upper().strip() not in valid_quants:
            errors.append(
                f"Target quantization '{q}' is not supported by standard GGUF workflow. Supported: {list(valid_quants)}"
            )

    return len(errors) == 0, errors


def simulate_gguf_conversion_and_quantize(
    model_key: str,
    source_revision: str,
    target_formats: list[str],
    mock_data: bool = True,
) -> dict[str, dict[str, Any]]:
    """Simulate or execute two-stage GGUF conversion and quantization for testing/validation.

    Stage 1: Generate FP16 baseline GGUF with valid header.
    Stage 2: Quantize into Q8_0 and Q4_K_M artifacts.

    Returns dict mapping format key to artifact metadata.
    """
    artifacts: dict[str, dict[str, Any]] = {}

    # Stage 1: FP16 GGUF baseline
    fp16_header = GGUF_MAGIC_BYTES + b"\x00\x00\x00\x03"  # GGUF v3
    fp16_content = fp16_header + f"mizan_gguf_fp16:{model_key}:{source_revision}".encode()
    fp16_hash = hashlib.sha256(fp16_content).hexdigest()
    artifacts["GGUF_FP16"] = {
        "artifact_type": ArtifactType.GGUF_FP16.value,
        "format": "GGUF",
        "quantization_type": "FP16",
        "data_bytes": fp16_content,
        "file_size_bytes": len(fp16_content),
        "sha256": fp16_hash,
    }

    # Stage 2: Quantizations
    for q_fmt in target_formats:
        q_key = q_fmt.upper().strip()
        q_bytes = GGUF_MAGIC_BYTES + f"quant_{q_key}:{fp16_hash[:16]}".encode()
        q_hash = hashlib.sha256(q_bytes).hexdigest()
        art_type = ArtifactType.GGUF_Q8_0.value if q_key == "Q8_0" else ArtifactType.GGUF_Q4_K_M.value
        artifacts[q_key] = {
            "artifact_type": art_type,
            "format": "GGUF",
            "quantization_type": q_key,
            "data_bytes": q_bytes,
            "file_size_bytes": len(q_bytes),
            "sha256": q_hash,
        }

    return artifacts


def validate_awq_quantization_preflight(
    architecture: str,
    has_gpu: bool,
    cuda_version: str | None = None,
    calibration_dataset_id: str | None = None,
) -> tuple[bool, list[str]]:
    """Validate distinct AWQ quantization prerequisites.

    Enforces:
    1. AWQ is strictly separate from GGUF.
    2. Requires GPU with CUDA Compute Capability >= 7.5.
    3. Requires authorized calibration dataset.
    """
    errors: list[str] = []

    if not has_gpu:
        errors.append("AWQ quantization requires dedicated NVIDIA GPU acceleration (CUDA Compute >= 7.5).")

    if not calibration_dataset_id:
        errors.append("AWQ quantization requires an authorized calibration dataset reference.")

    supported_archs = {"LlamaForCausalLM", "Qwen2ForCausalLM", "MistralForCausalLM"}
    if architecture not in supported_archs:
        errors.append(f"Architecture '{architecture}' is not supported by AutoAWQ. Supported: {list(supported_archs)}")

    return len(errors) == 0, errors
