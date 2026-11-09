# Mizan Milestone 8 — Hardware Knowledge Base Architecture

## 1. Executive Overview

Milestone 8 establishes the foundational compute infrastructure modeling, resource estimation, cost estimation, and financial governance layer for Mizan. It enables organizations to transparently predict memory footprints, verify host compatibility, estimate hourly infrastructure budgets, and enforce cryptographically attested human financial approvals before compute resources are provisioned.

Importantly, Milestone 8 strictly enforces the **Mandatory Free-Only Infrastructure Policy**: while the knowledge base models both cloud and local profiles for forward-looking analytical and comparison capabilities, any cloud provisioning attempt is **failsafe blocked by policy** (`ALLOW_PAID_COMPUTE=false`).

---

## 2. Hardware Profile Registry & Evidence Hierarchy

### 2.1 Reference Hardware Profiles

Mizan seeds four canonical hardware profiles in the database:

1. **`LOCAL_CPU_I5_8GB`**
   - **Category**: `LOCAL_WORKSTATION`
   - **Evidence Tier**: `MEASURED` (verified on actual development machine)
   - **Specs**: Intel(R) Core(TM) i5-6500 CPU @ 3.20GHz, 4 cores, 8,109 MB total RAM (~5,037 MB available after OS reservation).
   - **Capabilities**: CPU inference only. Quantizations: `Q4_K_M`, `Q8_0`.

2. **`REFERENCE_CPU_2VCPU_4GB`**
   - **Category**: `CLOUD_CPU`
   - **Evidence Tier**: `VENDOR_REFERENCE`
   - **Specs**: General Purpose Cloud 2 vCPU, 4,096 MB RAM (3,072 MB available).
   - **Capabilities**: Baseline CPU inference for lightweight utility models.

3. **`NVIDIA_T4_16GB`**
   - **Category**: `CLOUD_GPU`
   - **Evidence Tier**: `VENDOR_REFERENCE`
   - **Specs**: Cloud Host 4 vCPU, 15 GB RAM, NVIDIA Tesla T4 GPU (16,384 MB VRAM, 320 GB/s bandwidth).
   - **Capabilities**: Entry-level accelerator supporting GPU inference and parameter-efficient fine-tuning (LoRA). Supported formats: `FP16`, `Q8_0`, `Q4_K_M`, `AWQ`.

4. **`NVIDIA_A100_40GB`**
   - **Category**: `CLOUD_GPU`
   - **Evidence Tier**: `VENDOR_REFERENCE`
   - **Specs**: High-Memory Cloud Host 12 vCPU, 85 GB RAM, NVIDIA A100 Tensor Core GPU (40,960 MB VRAM, 1,555 GB/s bandwidth).
   - **Capabilities**: High-throughput datacenter accelerator supporting large models and full parameter fine-tuning. Supported formats: `FP16`, `Q8_0`, `Q4_K_M`, `AWQ`.

### 2.2 Evidence Classification Framework

Every hardware spec, benchmark, or estimate carries an explicit evidence tag:
- **`MEASURED`**: Directly captured from local system telemetry or bounded benchmarks on physical hardware.
- **`VENDOR_REFERENCE`**: Sourced from official hardware vendor datasheets and cloud documentation.
- **`ESTIMATED`**: Calculated deterministically via mathematical models and empirical formulas.
- **`SIMULATED`**: Generated via parametric modeling.
- **`USER_SUPPLIED`**: Input manually by tenant administrators.
- **`UNVERIFIED`**: Third-party or placeholder values awaiting formal attestation.

---

## 3. Safe Local Telemetry & CPU Benchmark

Host hardware inspection (`inspect_local_hardware`) operates with zero third-party drivers or external dependencies:
- On Windows: Queries `platform` and Windows Registry (`HARDWARE\DESCRIPTION\System\CentralProcessor\0`), with fallback memory inspection via `ctypes.windll.kernel32.GlobalMemoryStatusEx`.
- On Linux: Inspects `/proc/cpuinfo` and `/proc/meminfo`.
- Safe NVIDIA check: Tests `shutil.which("nvidia-smi")` without throwing exceptions if GPU drivers are absent.
- Bounded Benchmark (`run_bounded_cpu_benchmark`): Bounded matrix arithmetic test with a strict 5.0-second safety deadline and explicit garbage collection (`gc.collect()`) to guarantee zero memory leaks on 8 GB RAM systems.

---

## 4. Quantization Registry & Formulas

Effective bit representations account for tensor scaling overhead and block structures:
- **FP16**: 16.0 effective bits per parameter (2.0 bytes).
- **Q8_0**: 8.5 effective bits per parameter (8-bit quantization with 32-weight blocks).
- **Q4_K_M**: 4.9 effective bits per parameter (k-quantization medium scheme).
- **AWQ**: 4.5 effective bits per parameter (strictly GPU-only, requires CUDA Compute Capability $\ge$ 7.5).

```
Total Weight Memory (Bytes) = (Param Count * Effective Bits) / 8
```

---

## 5. Architectural Invariants

1. **Scope Boundaries**: Milestone 8 provides factual feasibility and compatibility assessments. It strictly avoids multi-objective recommendation scoring (reserved for M9) and training/quantization execution (reserved for M10).
2. **Fail-Closed Gate 2 Security**: Even when a Gate 2 financial approval is validly signed with Ed25519, `FinancialAuthorizationService` checks `settings.allow_paid_compute`. If `False`, execution returns `BLOCKED_BY_POLICY`.
3. **Decimal Precision Currency**: All pricing rates, totals, and budget calculations use Python `Decimal` with `ROUND_HALF_UP` rounding.
