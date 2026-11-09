# Milestone 9: Multi-Objective Optimization Model & Methodology

**Document Version:** 1.0.0  
**Status:** IMPLEMENTED & LOCALLY VERIFIED  
**Date:** 2026-11-09  

---

## 1. Centralized Objective Registry

The `ObjectiveRegistry` provides a single authoritative definition for all supported optimization dimensions across Mizan:

| Objective Key | Display Name | Category | Direction | Unit | Source Module & Field | Missing Data Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `aggregate_score` | Aggregate Rubric Score | `QUALITY` | `MAXIMIZE` | `pts` | M7 Trial `aggregate_score` | `PRESERVE_UNKNOWN` |
| `correctness` | Correctness & Exact Match | `QUALITY` | `MAXIMIZE` | `%` | M6 Eval `exact_match` | `PRESERVE_UNKNOWN` |
| `faithfulness` | Faithfulness Score | `QUALITY` | `MAXIMIZE` | `%` | M6 Eval `faithfulness` | `PRESERVE_UNKNOWN` |
| `groundedness` | Groundedness Score | `QUALITY` | `MAXIMIZE` | `%` | M6 Eval `groundedness` | `PRESERVE_UNKNOWN` |
| `citation_completeness`| Citation Completeness | `QUALITY` | `MAXIMIZE` | `%` | M6 Eval `citation_verification`| `PRESERVE_UNKNOWN` |
| `safety` | Safety & Abstention | `SAFETY_COMPLIANCE`| `MAXIMIZE` | `%` | M6 Eval `safety` | `PRESERVE_UNKNOWN` |
| `compliance` | Compliance Score | `SAFETY_COMPLIANCE`| `MAXIMIZE` | `%` | M6 Eval `compliance` | `PRESERVE_UNKNOWN` |
| `latency_p50_ms` | Median Latency (P50) | `PERFORMANCE` | `MINIMIZE` | `ms` | M7 Trial `latency_p50_ms` | `PRESERVE_UNKNOWN` |
| `latency_p95_ms` | Tail Latency (P95) | `PERFORMANCE` | `MINIMIZE` | `ms` | M7 Trial `latency_p95_ms` | `PRESERVE_UNKNOWN` |
| `execution_duration_ms`| Total Run Duration | `PERFORMANCE` | `MINIMIZE` | `ms` | M7 Trial `execution_duration_ms`| `PRESERVE_UNKNOWN` |
| `required_ram_mb` | Peak RAM / VRAM | `RESOURCE` | `MINIMIZE` | `MB` | M8 Estimator `peak_memory_mb` | `PRESERVE_UNKNOWN` |
| `artifact_size_mb` | Model Artifact Size | `RESOURCE` | `MINIMIZE` | `MB` | M8 Estimator `artifact_size_mb`| `PRESERVE_UNKNOWN` |
| `memory_headroom_mb` | Memory Headroom | `RESOURCE` | `MAXIMIZE` | `MB` | M8 Estimator `headroom_mb` | `PRESERVE_UNKNOWN` |
| `estimated_cost_usd` | Total Estimated Cost | `COST` | `MINIMIZE` | `USD`| M8 Estimator `total_estimated_cost`| `PRESERVE_UNKNOWN` |

---

## 2. Pre-Optimization Hard Constraint Filtering

Before multi-objective Pareto analysis or weighted scoring, candidates are evaluated against non-negotiable hard constraints via the `ConstraintEngine`:

1. **Trial Completion Invariant:** The candidate must be derived from an M7 experiment trial in `COMPLETED` status. `DRAFT`, `RUNNING`, `FAILED`, or `CANCELLED` trials are immediately excluded with an explicit reason.
2. **Gate 1 Approval Attestation:** When `require_gate1_approval` is active (default: true), the candidate must possess a verifiable Gate 1 approval attestation.
3. **Global Free-Only Policy Invariant:** When `ALLOW_PAID_PROVIDERS=false` (the strict non-negotiable default), workloads targeting cloud GPU or paid external infrastructure fail closed.
4. **Quality & Safety Thresholds:** Candidates failing minimum thresholds (e.g., `min_quality_score`, `min_safety_score`, `min_citation_score`) are classified as `INELIGIBLE`.
5. **Tail Latency Cap:** Candidates exceeding `max_p95_latency_ms` are rejected.
6. **Hardware Capacity Limits:** Workload memory requirements exceeding `max_ram_mb` or the target hardware profile's available capacity are rejected.
7. **Budget Constraint with Missing Cost Invariant:** If `max_budget_usd` is specified and the candidate's cost is missing (`UNKNOWN`), the candidate **fails closed** (`INSUFFICIENT_EVIDENCE`). Missing price is never assumed to be within budget.

---

## 3. Direction-Aware Metric Normalization

Metrics reside on fundamentally heterogeneous scales:
- Rubric Quality: $0.0 \dots 100.0\text{ pts}$
- Latency: $1.0 \dots 120,000.0\text{ ms}$
- Memory: $100.0 \dots 64,000.0\text{ MB}$
- Cost: $\$0.00 \dots \$1,000.00$

The `NormalizationService` maps all valid metrics to a unified $[0.0, 1.0]$ scale where $1.0$ is always most desirable and $0.0$ is least desirable:

### 3.1 Formulas
For a metric $v \in [\min_{\text{obs}}, \max_{\text{obs}}]$ with $\Delta = \max_{\text{obs}} - \min_{\text{obs}}$:

- **Maximize Objectives (Higher is Better):**
  $$v_{\text{norm}} = \frac{v - \min_{\text{obs}}}{\Delta}$$
- **Minimize Objectives (Lower is Better):**
  $$v_{\text{norm}} = \frac{\max_{\text{obs}} - v}{\Delta}$$
- **Zero-Variance / Constant Protection:**
  When $\min_{\text{obs}} = \max_{\text{obs}}$ (all candidates performed identically), $v_{\text{norm}} = 1.0$ to prevent division by zero and acknowledge that all candidates achieved parity.
- **Missing Value Handling:**
  If $v = \text{None}$ or unmeasured, $v_{\text{norm}} = \text{None}$. Missing values are never imputed as zero or best possible.

---

## 4. Optional Preference-Weighted Scoring

Weighted scoring is strictly optional and represents user preference alignment—**not** universal model quality.

### 4.1 Weight Validation Rules
1. Weights must be non-negative ($w_i \ge 0.0$).
2. Weights must be finite (no NaN, null, or $\pm\infty$).
3. Weights must sum to $1.0$ within a floating-point tolerance of $\pm 0.005$:
   $$\left|\sum_{i=1}^k w_i - 1.0\right| \le 0.005$$
4. All weighted keys must exist in the `ObjectiveRegistry`.

### 4.2 Score Calculation
For an eligible candidate with normalized vector $\mathbf{v}_{\text{norm}}$:
$$S_{\text{weighted}} = \sum_{i=1}^k w_i \cdot v_{\text{norm}, i}$$
Ineligible candidates receive $S_{\text{weighted}} = \text{None}$ and are excluded from competitive ranking.

### 4.3 Standard Presets
- `QUALITY_FIRST`: $60\%$ Quality, $20\%$ Latency, $20\%$ RAM
- `LATENCY_SENSITIVE`: $50\%$ Latency, $30\%$ Quality, $20\%$ RAM
- `RESOURCE_CONSTRAINED`: $50\%$ RAM, $25\%$ Quality, $25\%$ Latency
- `BALANCED`: $34\%$ Quality, $33\%$ Latency, $33\%$ RAM

---

## 5. Deterministic Sensitivity Analysis

The `SensitivityAnalysisEngine` perturbs baseline user weights by $\pm 25\%$ across individual dimensions and re-ranks eligible candidates:
1. Generates bounded alternative scenarios boosting each objective by $+25\%$, re-normalizing the remainder.
2. Tracks rank shifts, minimum rank, maximum rank, and rank variance:
   $$\text{Var}_{\text{rank}} = \text{rank}_{\max} - \text{rank}_{\min}$$
3. Classifies candidate stability:
   - **Stable / Robust:** $\text{Var}_{\text{rank}} \le 1$ position shift.
   - **Preference-Sensitive:** $\text{Var}_{\text{rank}} > 1$ position shift.
4. **Pareto Invariant:** Pareto frontier membership is computed strictly independently of weights and remains unchanged throughout sensitivity analysis.
