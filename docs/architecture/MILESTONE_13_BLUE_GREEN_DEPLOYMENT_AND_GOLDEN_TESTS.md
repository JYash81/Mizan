# Milestone 13 — Blue/Green Deployment Slots & Golden Test Runner Architecture

## 1. Blue/Green Architecture on Customer Infrastructure

Every installed application on a Customer Site maintains two logical deployment slots:
- **Slot A (Blue)**
- **Slot B (Green)**

At any time, one slot is **ACTIVE** (serving live inference traffic), while the alternate slot is **STAGED** or **EMPTY** (holding candidate releases).

### Memory-Constrained Staging Realism
On enterprise edge nodes with limited RAM (e.g. 8 GB or 16 GB), holding two uncompressed 8B models concurrently would cause Out-Of-Memory (OOM) failures.
The Mizan Blue/Green manager implements **unload-and-load staging semantics**:
- When staging a new candidate into the inactive slot, any old weights in that slot are explicitly unloaded first before new model tensors are mapped.
- Staged slot state transitions from `UNINITIALIZED` -> `LOADING` -> `READY` (or `UNHEALTHY`).

---

## 2. The 8 Golden Acceptance Test Categories

Before any candidate slot can receive live production traffic, it must execute a versioned **Golden Acceptance Test Suite**.

The suite evaluates 8 core operational categories:

| Category | Name | Purpose | Mandatory? |
| :--- | :--- | :--- | :--- |
| **`startup`** | Process Startup & Liveness | Verifies runtime process starts and `/live` probe returns 200 OK. | **Yes** |
| **`model_loading`** | Weights & Tensors Integrity | Confirms weights, tokenizer, and layers load without corruption or OOM. | **Yes** |
| **`inference_smoke`** | Deterministic Smoke Test | Sends standard baseline prompt; verifies non-empty response. | **Yes** |
| **`output_schema`** | Schema Compliance | Asserts response matches OpenAI chat completion schema. | **Yes** |
| **`rag_retrieval_citations`** | Local Grounded Citations | Verifies local vector lookup produces grounded citations with chunk IDs. | **Yes** |
| **`safety_abstention`** | Safety & Guardrails | Asserts adversarial queries trigger safe refusal/abstention. | **Yes** |
| **`offline_path`** | Zero Outbound Network | Verifies zero telemetry or external network calls occur during inference. | **Yes** |
| **`resource_limits`** | Slot Memory Budget | Asserts peak memory stays within allocated slot resource bounds. | No |

---

## 3. Strict Acceptance Gating

The slot manager strictly enforces that **mandatory test failures block slot promotion**:
- If any mandatory test case fails (e.g. safety refusal not triggered), the test run outcome is marked **`FAILED`**.
- The candidate slot's `readiness_state` is set to **`UNHEALTHY`**.
- Any operator attempt to promote the candidate slot via `/slots/activate` is **rejected with HTTP 412 Precondition Failed (`SlotActivationBlockedError`)**.
- Only when all mandatory test cases pass is `readiness_state` set to **`READY`** and `golden_test_status` set to **`PASSED`**.

---

## 4. Atomic Promotion & Manual Rollback

### Atomic Promotion
- Authorized human operator confirms promotion and provides an audit reason.
- Control plane / slot manager atomically switches traffic:
  - `RuntimeApplication.active_slot_name` updates to the candidate slot.
  - Candidate slot status becomes `ACTIVE`.
  - Previous active slot status becomes `STAGED` (preserving its configuration for instant rollback).
  - Appends an immutable audit event to `RuntimeActivationEvent`.

### Manual Rollback
- If a production issue is noticed after promotion, the operator can trigger instant manual rollback via the console or API.
- The alternate slot is immediately reinstated as active.
- A rollback audit record is appended with reason prefixed by `ROLLBACK: <reason>`.
