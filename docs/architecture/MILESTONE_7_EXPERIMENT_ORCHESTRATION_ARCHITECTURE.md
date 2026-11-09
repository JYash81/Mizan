# MIZAN Experiment Orchestration & Trial Matrix Engine Architecture (Milestone 7)

## 1. System Overview

The Mizan **Model Experimentation, Trial Matrix & Experiment Orchestration Engine** (Milestone 7) bridges verified business knowledge and evaluation suites with controlled, reproducible experimental trials.

The central question Milestone 7 answers is:
> **"When we change an AI configuration (chunk size, overlap, retrieval depth, prompt strategy, model/provider), how does its measured performance differ against the same approved dataset and evaluation suite?"**

The architecture complies with the **Mandatory Free-Only Infrastructure Policy**: all trial evaluations execute deterministically on local CPU with zero cloud API spend, zero GPU requirements, and sequential execution (concurrency = 1) tailored for an 8 GB RAM Windows workstation.

```
+----------------------------------------------------------------------------------------------------+
|                                    GATE 1 APPROVAL & PROVENANCE                                     |
|  [Masked Dataset Bucket] -> [Gate 1 Approval Digest Verification] -> [Frozen Evaluation Suite (M6)]|
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                      TRIAL MATRIX GENERATOR                                        |
|  * Preset Matrices: chunk_sensitivity, retrieval_depth, prompt_strategy, chunk_and_retrieval       |
|  * Parametric Variations: Cartesian product expansion clamped strictly to 3..9 unique trials       |
|  * Manual Authoring: Custom operator-defined trial parameter sets                                  |
|  * Canonical SHA-256 Digest Verification & Duplicate Rejection                                     |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                DETERMINISTIC EXPERIMENT STATE MACHINE                              |
|  * Experiment: DRAFT -> VALIDATING -> READY -> QUEUED -> RUNNING -> COMPLETED / COMPLETED_W_ERRORS |
|  * Trial:      PENDING -> VALIDATING -> QUEUED -> RUNNING -> COMPLETED / FAILED / CANCELLED        |
|  * Full Audit Trail: experiment_events records every status delta with caller metadata             |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                           BOUNDED SEQUENTIAL TRIAL EXECUTION ENGINE                                |
|  * Concurrency = 1 (Local CPU, 8 GB RAM protective isolation)                                      |
|  * Execution delegated to M6 EvaluationService producing real EvaluationRun records                |
|  * Strict Failure Isolation: Single trial failure does not abort experiment                        |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                FACTUAL COMPARISON & REPORT EXPORTS                                 |
|  * Aligned multi-trial metric matrix with missing value preservation (None, not 0.0)               |
|  * Factual Observations only (Highest observed score, Lowest observed latency)                     |
|  * STRICTLY NO M9 CLAIMS: No Pareto frontiers, no "winner" labels, no weighted recommendations     |
|  * Multi-format export: JSON, Markdown, and CSV                                                   |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Invariants & Architectural Guardrails

### Invariant 1: Gate 1 Approval Required (Fail-Closed)
- Every experiment must link to a dataset version with an approved `Gate1Approval` record.
- Unapproved datasets, pending reviews, or raw customer documents are strictly rejected with `HTTP 403 Forbidden` / `ValueError`.
- Cryptographic verification binds the experiment's `dataset_digest` to the Gate 1 approved output digest.

### Invariant 2: Holdout Split Protection
- To prevent hyperparameter overfitting on test benchmarks, experiments tuning ordinary trials strictly reject `SplitType.HOLDOUT`.
- Only `SplitType.VALIDATION` and `SplitType.TEST` are permitted for experiment execution.
- Any attempt to configure an experiment with `split_type="HOLDOUT"` is rejected by schema validation.

### Invariant 3: Canonical Configuration Digest & Deduplication
- Configuration dictionaries are serialized canonically: recursive key sorting, compact formatting (`separators=(",", ":")`), and SHA-256 hashing.
- If any two trials within an experiment produce identical configuration digests, the entire matrix is rejected at validation time before execution starts.

### Invariant 4: Bounded Trial Counts (3..9 Unique Trials)
- To maintain computational feasibility on local CPU, every experiment matrix must contain between **3 and 9 unique trials**.
- Matrices with fewer than 3 trials fail validation with an informative error.
- Parametric grids generating more than 9 combinations are deterministically clamped to the first 9 unique configurations.

### Invariant 5: Local CPU Resource Isolation (Sequential Execution)
- Concurrency is strictly bounded to `concurrency = 1`.
- Trials execute sequentially in order of `trial_number` (1..9).
- Prevents memory spikes, process thrashing, or embedded Qdrant database lock contention on local developer hardware.

### Invariant 6: Failure Isolation & Partial Completion
- A trial-level failure (e.g. timeout, transient provider error) is caught and isolated to that specific trial (`TrialStatus.FAILED`).
- Remaining trials continue executing.
- An experiment with at least one succeeded and at least one failed trial transitions to `ExperimentStatus.COMPLETED_WITH_ERRORS`.
- An experiment transitions to `FAILED` only if all trials fail.

### Invariant 7: Factual Comparison Only (Strict Scope Isolation)
- **Milestone 8 (Hardware Compatibility & Gate 2) and Milestone 9 (Recommendation Engine) are strictly out of scope.**
- The comparison service and UI provide only objective, factual observations:
  - *"Highest observed score for this metric: 88.5% on Trial 2"*
  - *"Lowest observed latency: 120 ms on Trial 1"*
- The system never outputs Pareto-optimal frontiers, weighted recommendation scoring, "recommended configuration", or "winner" badges.

---

## 3. Deterministic State Machines

### Experiment State Transition Table

| Source Status | Allowed Target Statuses | Trigger / Conditions |
|---|---|---|
| `DRAFT` | `VALIDATING`, `READY`, `CANCEL_REQUESTED`, `CANCELLED` | Matrix generation, configuration update, cancellation |
| `VALIDATING` | `READY`, `DRAFT`, `FAILED` | Matrix validation passes or fails |
| `READY` | `QUEUED`, `RUNNING`, `VALIDATING`, `CANCEL_REQUESTED`, `CANCELLED` | Execution triggered by user |
| `QUEUED` | `RUNNING`, `CANCEL_REQUESTED`, `CANCELLED` | Worker picks up experiment |
| `RUNNING` | `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`, `CANCEL_REQUESTED`, `CANCELLED` | All trials finish, partial failure, total failure, or user cancel |
| `CANCEL_REQUESTED`| `CANCELLED`, `COMPLETED_WITH_ERRORS` | Execution halts safely |
| `COMPLETED` | *(Terminal)* | All trials succeeded |
| `COMPLETED_WITH_ERRORS` | *(Terminal)* | At least one trial succeeded and one failed |
| `FAILED` | *(Terminal)* | All trials failed or preflight fatal error |
| `CANCELLED` | *(Terminal)* | Experiment was cancelled |

### Trial State Transition Table

| Source Status | Allowed Target Statuses | Trigger / Conditions |
|---|---|---|
| `PENDING` | `VALIDATING`, `QUEUED`, `RUNNING`, `SKIPPED`, `CANCELLED` | Trial queueing or setup |
| `VALIDATING` | `QUEUED`, `RUNNING`, `FAILED` | Config preflight validation |
| `QUEUED` | `RUNNING`, `CANCELLED` | Runner begins executing trial |
| `RUNNING` | `COMPLETED`, `FAILED`, `CANCEL_REQUESTED`, `CANCELLED` | Trial evaluation finishes or errors |
| `CANCEL_REQUESTED`| `CANCELLED` | Safe shutdown |
| `COMPLETED` | *(Terminal)* | M6 evaluation run completed successfully |
| `FAILED` | *(Terminal)* | Evaluation failed with error summary |
| `SKIPPED` | *(Terminal)* | Trial skipped due to user configuration |
| `CANCELLED` | *(Terminal)* | Trial cancelled |

---

## 4. Trial Matrix Generation Strategies

### Standard Presets (`matrix/presets.py`)
1. **`chunk_sensitivity` (4 trials):**
   - Varies chunk size: `[256, 512, 1024, 2048]` with proportional 10% overlap and constant `top_k=5`.
2. **`retrieval_depth` (4 trials):**
   - Varies retrieval depth: `top_k in [3, 5, 8, 12]` with constant chunk size 512.
3. **`prompt_strategy` (3 trials):**
   - Varies prompt instructions: `concise`, `detailed`, `chain_of_thought` with constant chunk size 512 and `top_k=5`.
4. **`chunk_and_retrieval` (9 trials):**
   - 3x3 grid testing chunks `[256, 512, 1024]` across `top_k in [3, 5, 8]`.

### Parametric Variation (`matrix/generator.py`)
- Accepts a baseline configuration and parameter variation lists:
  - `chunk_sizes: list[int]`
  - `top_ks: list[int]`
  - `prompt_strategies: list[str]`
  - `models: list[str]`
- Computes Cartesian product, filters duplicate digests, enforces parameter bounds (chunk size 50..5000, overlap < chunk_size, top_k 1..20), and clamps output to 3..9 unique trials.

---

## 5. Sequential Execution & Metric Alignment

### Execution Engine (`services/execution_service.py`)
- Bounded runner iterates over trials sequentially:
  ```python
  for trial in experiment.trials:
      if experiment.status == ExperimentStatus.CANCEL_REQUESTED:
          break
      # 1. Transition trial to RUNNING
      # 2. Invoke M6 EvaluationService.execute_evaluation_run(...)
      # 3. Extract aggregate score, score breakdown, and latency percentiles
      # 4. Link evaluation_run_id to trial
      # 5. Transition trial to COMPLETED (or FAILED on error)
  ```
- Uses M6's deterministic evaluation pipeline, scoring the trial across 11 local CPU metrics.

### Comparison Service (`services/comparison_service.py`)
- Gathers all evaluation runs linked to the experiment's trials.
- Constructs an aligned metric matrix where rows are metrics and columns are trials.
- **Missing Value Handling:** Missing or uncalculated metrics are preserved as `null` (`None`), never defaulted to `0.0`.
- Generates **Metric Observations**:
  - `highest_observed`: Identifies trial with maximum score.
  - `lowest_observed`: Identifies trial with minimum latency.
  - `variance`: Spread of scores across trials.
  - Highlights strictly factual observations without subjective recommendations.

---

## 6. Database Schema Design

```
+--------------------------------------------------------------------------+
|                               experiments                                |
+--------------------------------------------------------------------------+
| id                       UUID PRIMARY KEY                                |
| organization_id          UUID FK -> organizations.id                     |
| workspace_id             UUID FK -> workspaces.id                        |
| name                     VARCHAR(255) NOT NULL                           |
| slug                     VARCHAR(255) NOT NULL (UNIQUE per workspace)    |
| description              TEXT                                            |
| status                   VARCHAR(50) NOT NULL (ExperimentStatus)         |
| dataset_version_id       UUID FK -> dataset_versions.id                  |
| dataset_digest           VARCHAR(64) NOT NULL                            |
| evaluation_suite_version_id UUID FK -> evaluation_suite_versions.id      |
| suite_digest             VARCHAR(64) NOT NULL                            |
| split_type               VARCHAR(30) NOT NULL (VALIDATION / TEST)        |
| baseline_configuration_json TEXT NOT NULL                                |
| baseline_configuration_digest VARCHAR(64) NOT NULL                       |
| matrix_generation_strategy VARCHAR(50) NOT NULL                          |
| total_trials             INTEGER NOT NULL DEFAULT 0                      |
| completed_trials         INTEGER NOT NULL DEFAULT 0                      |
| failed_trials            INTEGER NOT NULL DEFAULT 0                      |
| started_at               DATETIME (UTC)                                  |
| completed_at             DATETIME (UTC)                                  |
| created_at               DATETIME (UTC) NOT NULL                         |
| updated_at               DATETIME (UTC) NOT NULL                         |
+--------------------------------------------------------------------------+
                                     | 1
                                     |
                                     | N
+--------------------------------------------------------------------------+
|                            experiment_trials                             |
+--------------------------------------------------------------------------+
| id                       UUID PRIMARY KEY                                |
| organization_id          UUID FK -> organizations.id                     |
| workspace_id             UUID FK -> workspaces.id                        |
| experiment_id            UUID FK -> experiments.id (CASCADE DELETE)      |
| trial_number             INTEGER NOT NULL (1..9, UNIQUE per experiment)  |
| name                     VARCHAR(255) NOT NULL                           |
| status                   VARCHAR(50) NOT NULL (TrialStatus)              |
| configuration_json       TEXT NOT NULL                                   |
| configuration_digest     VARCHAR(64) NOT NULL                            |
| evaluation_run_id        UUID FK -> evaluation_runs.id (NULLABLE)        |
| aggregate_score          FLOAT NULLABLE                                  |
| score_breakdown_json     TEXT NULLABLE                                   |
| latency_p50_ms           FLOAT NULLABLE                                  |
| latency_p95_ms           FLOAT NULLABLE                                  |
| latency_p99_ms           FLOAT NULLABLE                                  |
| error_summary            TEXT NULLABLE                                   |
| started_at               DATETIME (UTC)                                  |
| completed_at             DATETIME (UTC)                                  |
| created_at               DATETIME (UTC) NOT NULL                         |
| updated_at               DATETIME (UTC) NOT NULL                         |
+--------------------------------------------------------------------------+
                                     | 1
                                     |
                                     | N
+--------------------------------------------------------------------------+
|                            experiment_events                             |
+--------------------------------------------------------------------------+
| id                       UUID PRIMARY KEY                                |
| experiment_id            UUID FK -> experiments.id (CASCADE DELETE)      |
| trial_id                 UUID FK -> experiment_trials.id (NULLABLE)      |
| previous_status          VARCHAR(50) NULLABLE                            |
| new_status               VARCHAR(50) NOT NULL                            |
| event_type               VARCHAR(50) NOT NULL                            |
| message                  TEXT NULLABLE                                   |
| metadata_json            TEXT NULLABLE                                   |
| created_by_user_id       UUID FK -> users.id (NULLABLE)                  |
| created_at               DATETIME (UTC) NOT NULL                         |
+--------------------------------------------------------------------------+
```

---

## 7. Frontend Architecture

The Experiment Lab UI is organized under `frontend/src/features/experiments/`:
- **`ExperimentListPage.tsx`**: Searchable catalog of experiments, status badges, trial progress bars, date formatting, and new experiment trigger.
- **`ExperimentWizardPage.tsx`**: 5-step guided wizard:
  1. *Provenance:* Select Gate 1 approved dataset and frozen evaluation suite.
  2. *Baseline:* Configure baseline chunk size, overlap, top_k, model, and prompt strategy.
  3. *Matrix Presets:* Select from standard presets or define parametric variations.
  4. *Preflight:* Verify canonical digests and preview trial configurations.
  5. *Launch:* Create experiment and optionally launch immediate sequential execution.
- **`ExperimentDetailPage.tsx`**: Provenance badges, execution progress, trial matrix data table, live trial status indicators, trial detail drawer (scores, latencies, configuration JSON), run comparison CTA, and multi-format report exports.
- **`ExperimentComparisonPage.tsx`**: Side-by-side trial comparison matrix, configuration differences table, aligned metric scores, and factual observations card.
