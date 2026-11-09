# Milestone 10: Quantization and GGUF Conversion

## 1. Overview & Objectives

Post-training quantization reduces the memory footprint and bandwidth demands of large language models, enabling efficient CPU and edge deployment. Milestone 10 establishes deterministic, audited quantization workflows for:
1. **GGUF (GPT-Generated Unified Format):** Optimized for CPU and mixed CPU/GPU inference via `llama.cpp`.
2. **AWQ (Activation-aware Weight Quantization):** Optimized for low-latency GPU deployment with preserved saliency weights.

---

## 2. GGUF Two-Stage Conversion Architecture

Direct quantization of arbitrary raw model files can introduce non-deterministic tensor layouts. M10 enforces a strictly separated two-stage workflow:

```
+---------------------------+
| Hugging Face Model Weights|
| (.safetensors / FP16)     |
+---------------------------+
              |
              | Stage 1: Conversion (convert_hf_to_gguf.py)
              v
+---------------------------+
|     Unquantized GGUF      |
|    (FP16 or BF16 GGUF)    |
+---------------------------+
              |
              | Stage 2: Quantization (llama-quantize)
              +-----------------------------+
              |                             |
              v                             v
+---------------------------+ +---------------------------+
|      GGUF Q8_0 (8-bit)    | |     GGUF Q4_K_M (4-bit)   |
|   Preserved Quality Tier  | |    Balanced Memory Tier   |
+---------------------------+ +---------------------------+
```

### Stage 1: Hugging Face to GGUF FP16
- Extracts tokenizer vocabulary, merges, chat template, and metadata.
- Converts tensors into standardized contiguous GGUF tensor format.
- Generates base unquantized intermediate artifact with magic header `GGUF` (`0x46554747`).

### Stage 2: Deterministic Quantization
- **`Q8_0`:** 8-bit symmetric quantization. Preserves >99.5% baseline model perplexity. Ideal when system memory allows (e.g. 1B models on 4 GB RAM).
- **`Q4_K_M`:** 4-bit k-quant with medium block structure (attention and feed-forward layers quantized with mixed 4-bit and 6-bit scales). Delivers ~65% memory reduction with <1.5% quality drop.

### Anti-Requantization Policy:
M10 strictly forbids re-quantizing an already quantized model (e.g. attempting to convert a `Q4_K_M` GGUF into `Q8_0` or `Q2_K`). Requantizing lossy weights compounds distortion and fails-closed with `RequantizationForbiddenError`.

---

## 3. AWQ Quantization Workflow

AWQ is implemented as a **completely independent quantization pipeline** from GGUF:
- **Salience Protection:** Analyzes activation distributions using a small calibration dataset (128-512 tokens from Gate 1 approved data) to identify the top 1% salient weights.
- **Hardware Requirement:** AWQ requires dedicated GPU acceleration for calibration and inference. It is strictly designated for Colab Free T4 GPU or GPU servers, and cannot run on local CPU-only hardware.
- **Output:** Staged safetensors model with quantized INT4 weights and FP16 scales.

---

## 4. Staging Verification & Regression Visibility

Every quantized artifact staged in Milestone 10 undergoes automated integrity checks:
1. **Magic Header Inspection:** Validates binary magic bytes (`GGUF` for GGUF files; valid JSON header for safetensors).
2. **File Size Boundaries:** Ensures file size is within theoretical bounds for the parameter count and bit depth (e.g. a 1B Q4_K_M file cannot exceed 1.5 GB).
3. **M6 Evaluation Linkage:** Staged quantized models are evaluated against the frozen benchmark suite to measure the exact quality delta against the unquantized base model:
   $$\Delta_{\text{quality}} = \text{Score}_{\text{quantized}} - \text{Score}_{\text{base}}$$
   If $\Delta_{\text{quality}} < 0$, the regression is visibly tagged across UI cards and API responses. Concealment of quantization loss is strictly prohibited.
