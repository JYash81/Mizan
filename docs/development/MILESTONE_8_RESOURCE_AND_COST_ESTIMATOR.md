# Milestone 8: Resource and Cost Estimator Implementation Guide

## 1. Resource Estimation Mathematical Model

The resource estimator (`ResourceEstimatorService` in `app/modules/hardware/resource_estimator.py`) calculates deterministic memory footprints across five components:

### 1.1 Weights Memory & Artifact Size
- **Weight Memory (MB)**:
  $$\text{Weight MB} = \frac{\text{Parameter Count} \times \text{Effective Bits}}{8 \times 1024 \times 1024}$$
- **Artifact Size (MB)**: Includes safetensors / GGUF container headers and tensor metadata tables ($+2\%$ overhead):
  $$\text{Artifact MB} = \text{Weight MB} \times 1.02$$

### 1.2 KV Cache Memory
When architectural metadata is provided:
$$\text{KV Cache Bytes} = 2 \times \text{layers} \times \text{kv\_heads} \times \text{head\_dim} \times 2.0 \times \text{context\_len} \times \text{batch\_size}$$
Fallback heuristic when layer/head metadata is missing:
$$\text{KV Cache MB} = \frac{\text{Parameter Count}}{10^9} \times 0.20 \times \frac{\text{context\_len}}{1024} \times \text{batch\_size}$$

### 1.3 Execution Overhead by Mode
- **`INFERENCE_CPU`**:
  $$\text{Runtime Overhead} = \max(256\text{ MB}, \text{Weight MB} \times 0.08) + \text{Activation MB}$$
- **`INFERENCE_GPU`**:
  $$\text{Runtime Overhead} = 512\text{ MB (CUDA Context)} + \text{Activation MB}$$
- **`FINE_TUNE_LORA`**:
  Includes $1\%$ trainable adapter weights (FP16), AdamW optimizer states for adapters ($8$ bytes/param), gradients ($4$ bytes/param), and activations ($25\%$ weight memory).
- **`FINE_TUNE_FULL`**:
  Includes FP32 Adam optimizer states ($16$ bytes/param), FP32 gradients ($4$ bytes/param), and full backward activations.

### 1.4 Safety Headroom Buffer & Feasibility Rules
- **Safety Margin**: A mandatory $15\%$ buffer ($\text{factor} = 1.15$) is applied to peak execution memory:
  $$\text{Required With Margin} = \text{Peak Memory} \times 1.15$$
  $$\text{Headroom} = \text{Available Memory} - \text{Required With Margin}$$
- **Feasibility Classification**:
  - `FEASIBLE_ESTIMATE`: Headroom $\ge 0\text{ MB}$.
  - `LIKELY_FEASIBLE`: Headroom between $-512\text{ MB}$ and $0\text{ MB}$ (fits raw peak memory, but tight safety buffer).
  - `NOT_FEASIBLE`: Headroom $< -512\text{ MB}$, or GPU execution requested on CPU-only hardware, or AWQ requested on CPU.

---

## 2. Infrastructure Cost Estimator

The cost estimator (`CostEstimatorService` in `app/modules/cost/cost_estimator.py`) enforces strict financial integrity:

### 2.1 Decimal Arithmetic Invariant
- Floating-point representations (`float`) are strictly forbidden for currency calculations to prevent binary rounding inaccuracies (e.g. $0.1 + 0.2 \ne 0.3$).
- All rates, durations, and totals use Python's `Decimal` type with `ROUND_HALF_UP` rounding to two decimal places.

### 2.2 Missing Price Invariant
- If a pricing entry does not exist in the catalog, the system **never defaults to $0.00**.
- The service returns status `PRICE_UNAVAILABLE` and total cost `UNKNOWN` with explicit warnings.

### 2.3 Zero-Spend Local Invariant
- Workloads targeting the `local` provider or `LOCAL_CPU_I5_8GB` profile evaluate to status `ZERO_SPEND_LOCAL` with exactly `$0.00` total cost.

### 2.4 Billing Unit Alignment
- Durations are aligned with provider billing units (e.g. 3,600-second blocks for GCP/AWS VMs). A 2.5-hour workload is billed as 3.0 billable hours.
