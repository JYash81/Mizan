# Milestone 10: Model Building, Fine-Tuning, Quantization & Colab Lab Architecture

## 1. System Purpose & Core Principles

Milestone 10 turns a validated AI configuration (identified through Milestone 6 evaluation suites, Milestone 7 controlled experiments, Milestone 8 hardware/cost estimation, or Milestone 9 Pareto recommendations) into an **auditable, reproducible model-building workflow**.

### Core Guiding Principles:
1. **Strict Free-Only Infrastructure Policy ($0.00 Spend):** Zero cloud provisioning, zero paid APIs, zero automated billing. All local execution is restricted to safe CPU smoke tests on miniature models (<150M parameters). GPU training workloads utilize user-operated Google Colab Free (T4 GPU).
2. **Strict Milestone Boundaries (Pre-M11 Boundary):** M10 creates and cryptographically validates `StagedModelArtifact` records. It does **not** publish release artifacts, grant Gate 3 release approvals, or register models for production runtime (strictly owned by Milestone 11).
3. **Deterministic Reproducibility:** Every build run generates a canonical RFC 8785 JSON manifest with a deterministic SHA-256 `manifest_digest`. Base model revisions are locked to immutable commit SHAs.
4. **Data Privacy & Gate 1 Integrity:** Training data requires prior Gate 1 approval. Exporting masked datasets to external Colab runtimes requires explicit, time-bounded `ExternalProcessingAuthorization`. Raw customer documents are never exported.
5. **Evaluation Integration & Regression Visibility:** Staged artifacts link to M6 evaluation runs to assess quality deltas. Quality regressions post-adaptation or quantization are prominently highlighted and never concealed.

---

## 2. Core Entities & Relational Schema

```
                                 +-----------------------+
                                 |      ModelSource      |
                                 +-----------------------+
                                             | 1
                                             |
                                             v *
+-----------------------+        +-----------------------+        +-----------------------+
|   ModelBuildRecipe    | 1    * |     ModelBuildRun     | 1    * | ModelBuildCheckpoint  |
+-----------------------+--------+-----------------------+--------+-----------------------+
                                             | 1
                      +----------------------+----------------------+
                      | *                                           | *
                      v                                             v
         +-----------------------+                     +-----------------------+
         |  StagedModelArtifact  |                     |  ModelEvaluationLink  |
         +-----------------------+                     +-----------------------+
                      | 1                                           |
                      +---------------------------------------------+
```

### Table Specifications:

- `model_sources`: Curated catalog of open weights (Tiny Llama 35M, SmolLM2 135M, Llama 3.2 1B, Qwen 2.5 0.5B) with immutable Git commit SHAs, architecture identifiers, parameter counts, context lengths, and license metadata.
- `model_build_recipes`: Standard recipes (`SMOKE_TEST_CPU`, `LORA_COLAB_FREE`, `QLORA_COLAB_FREE`, `GGUF_CONVERT_AND_QUANTIZE`, `AWQ_QUANTIZE_COMPATIBLE`) with JSON schema, pinned dependencies, architecture compatibility maps, and resource limits.
- `external_processing_authorizations`: Human authorizations for exporting Gate 1 approved masked datasets to ephemeral Colab runtimes.
- `model_build_runs`: State machine tracking execution lifecycle (`DRAFT`, `READY`, `RUNNING`, `CHECKPOINTED`, `COMPLETED`, `BLOCKED_BY_RESOURCES`, `FAILED`). Stores canonical RFC 8785 manifest, manifest digest, preflight snapshots, and partition digests.
- `model_build_checkpoints`: Atomic checkpoint records with step numbers, epochs, storage references, metrics, and configuration hashes.
- `model_build_events`: Structured audit log capturing lifecycle transitions, preflight results, and operator actions.
- `staged_model_artifacts`: Staged build artifacts (`LORA_ADAPTER`, `GGUF_QUANTIZED`, `AWQ_QUANTIZED`, `MERGED_MODEL`) with SHA-256 hashes, file format verification, and `is_staged_for_m11 = True`.
- `model_evaluation_links`: Quality links to M6 `EvaluationRun`, computing quality deltas (`score - base_score`) and transparently flagging regressions.

---

## 3. Resource Preflight & Feasibility Enforcement

Before any build run is authorized, M10 runs a resource preflight check integrating Milestone 8 hardware models:

$$\text{Weight RAM (MB)} = \frac{\text{Params} \times \text{Bytes Per Weight}}{1024^2}$$

$$\text{KV Cache (MB)} = \frac{2 \times \text{Layers} \times \text{KV Heads} \times \text{Head Dim} \times 2 \times \text{Context Length} \times \text{Batch Size}}{1024^2}$$

$$\text{Disk Requirement (MB)} = \text{Download Size} + \text{Base Weights} + (3 \times \text{Checkpoint Buffer}) + \text{Output Artifact} + 2048\text{ MB Safety Headroom}$$

### Host Restrictions:
- **Local Workstation (Core i5, 8 GB RAM):** Restricted to CPU execution, maximum 4096 MB working RAM, and models $\le 150\text{M}$ parameters. Any GPU recipe or model exceeding limits is marked `NOT_FEASIBLE` and transitions to `BLOCKED_BY_RESOURCES`.
- **Google Colab Free (NVIDIA T4 16 GB):** Feasible for parameter-efficient LoRA / QLoRA up to 3B parameters with 15,360 MB VRAM headroom.

---

## 4. Checkpoint Resumption & Integrity

Checkpoints are saved atomically into `StorageBucket.ARTIFACTS`. Resumption strictly requires:
1. Matching base model revision SHA.
2. Matching training dataset version digest.
3. Matching canonical manifest digest.
4. Consecutive checkpoint and step numbers.
Attempts to resume with mismatched datasets or altered configurations fail-closed with `CheckpointValidationError`.

---

## 5. Security & Tenant Isolation

1. **Anti-Enumeration:** All workspace endpoints verify tenant ownership before querying runs or artifacts. Foreign workspace requests return 404 Not Found.
2. **RBAC Permissions:**
   - `MODEL_BUILDING_READ`: View catalog, recipes, runs, and staged artifacts.
   - `MODEL_BUILDING_CREATE`: Authorize and configure new build runs.
   - `MODEL_BUILDING_EXECUTE`: Trigger local smoke test execution.
   - `MODEL_BUILDING_EXPORT`: Export Colab `.ipynb` notebooks and manifests.
   - `MODEL_BUILDING_AUTHORIZE_EXTERNAL`: Grant external export authorizations.
   - `MODEL_BUILDING_IMPORT`: Import and stage external execution outputs.
