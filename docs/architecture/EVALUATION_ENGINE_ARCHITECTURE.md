# MIZAN Evaluation Engine Architecture (Milestone 6)

## 1. System Overview

The Mizan **Exam & Evaluation Engine** (Milestone 6) provides automated, domain-grounded evaluation suite generation, human verification workflows, multi-dimensional scoring rubrics, and reproducible benchmark execution against AI systems (RAG pipelines, local LLMs, and external models).

The architecture strictly complies with the **Mandatory Free-Only Infrastructure Policy**: all 11 evaluation metrics run deterministically on local CPU with zero cloud API dependencies, zero GPU requirements, and zero additional budget spend ($0.00).

```
+----------------------------------------------------------------------------------------------------+
|                                    GATE 1 APPROVAL ENFORCEMENT                                     |
|  [Raw Documents] -> [Sensitive Data Masking] -> [Gate 1 Human Sign-off] -> [Masked Dataset Bucket]|
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                      EXAM GENERATION SUBSYSTEM                                     |
|  * Rule-Based Generator (Sentence Offset Tracking, Extraction, Inversion)                          |
|  * 8 Question Categories: FACTUAL, CONCEPTUAL, PROCEDURAL, COMPARISON, MULTI_HOP,                  |
|    NUMERICAL, DOCUMENT_SPECIFIC, UNANSWERABLE (Abstention Tests)                                   |
|  * Deterministic Split Hashing (SHA-256): 60% DEVELOPMENT, 20% VALIDATION, 20% HOLDOUT              |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                      HUMAN REVIEW & CURATION                                       |
|  * State Machine: GENERATED -> NEEDS_REVIEW -> HUMAN_VERIFIED / REJECTED / FLAGGED                 |
|  * Manual Case Authoring with Reference Ground Truth                                              |
|  * Immutable Suite Freezing -> Canonical SHA-256 Digest Attestation                                |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                  EVALUATION EXECUTION & SCORING                                    |
|  * Multi-Dimensional Rubric Engine (Weighted 0-100 Score Aggregation)                              |
|  * 11 Deterministic Local CPU Evaluators:                                                          |
|    1. Exact Match                    5. Context Relevance              9. Appropriate Abstention   |
|    2. Token F1                       6. Groundedness                   10. Safety (Zero PII Leaks) |
|    3. Keyword Coverage               7. Faithfulness                   11. Business Compliance     |
|    4. Retrieval Quality (P, R, MRR)  8. Citation Verification                                      |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                    REPORTING & AUDIT EXPORTS                                       |
|  * Comprehensive Evaluation Reports in JSON, Markdown, and CSV Formats                             |
|  * P50 / P95 / P99 Latency Profiles & Zero Raw PII Attestation                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Invariants & Security Boundaries

1. **Gate 1 Approval Prerequisite:**
   - Exam generation strictly requires prior human approval of the masked dataset.
   - Any attempt to generate questions from an unapproved or raw dataset version fails closed with `HTTP 403 Forbidden`.
   - Raw customer documents never enter the examination generation pipeline.

2. **Reference Answer Confidentiality:**
   - Expected reference answers stored in `EvaluationCase.expected_answer` are never supplied to the generation context of the target model under test.
   - Ground truth answers are strictly isolated and only accessed by scoring evaluators post-generation.

3. **Immutable Suite Versioning & Attestation:**
   - Once finalized, an `EvaluationSuiteVersion` cannot be altered or appended to.
   - The suite's questions, expected answers, categories, splits, and rubric configuration are canonically serialized and hashed using SHA-256 (`canonical_digest_sha256`).
   - If questions must be added or edited, a new version must be finalized.

4. **Zero-Cost CPU Determinism:**
   - All 11 evaluation metrics run on CPU without external API calls or GPU compute.
   - Metrics are deterministic, reproducible, and portable across development workstations and production servers.

---

## 3. Database Schema Design

The evaluation schema is fully managed via SQLAlchemy and Alembic migration `20261108_0007_evaluation_engine.py`:

- **`evaluation_suites`:** Organization- and workspace-scoped container for evaluation criteria and question collections.
- **`evaluation_suite_versions`:** Immutable, cryptographically attested snapshots of reviewed cases with version numbers.
- **`evaluation_cases`:** Individual examination questions, expected answers, categories, difficulty, split assignments, source document/chunk references, and review state.
- **`evaluation_rubrics`:** Multi-dimensional scoring templates defining criteria weights and threshold expectations.
- **`rubric_criteria`:** Individual criterion configurations linked to specific deterministic scoring methods.
- **`evaluation_runs`:** Benchmark execution instances linking a model target to an immutable suite version and rubric.
- **`evaluation_case_results`:** Per-case execution results storing actual generated answers, retrieved chunks, citations, latency, and case-level scores.
- **`evaluation_metric_results`:** Fine-grained metric score records per case result with evaluator versions and diagnostic details.
- **`evaluation_reviews`:** Human audit trail logging every reviewer approval, rejection, edit, and comment.

---

## 4. Question Categories & Split Allocations

The engine supports 8 question categories grounded in business knowledge:
- **`FACTUAL`:** Direct information retrieval and statement verification.
- **`CONCEPTUAL`:** Principle and high-level guideline comprehension.
- **`PROCEDURAL`:** Step-by-step business workflows, requirements, and escalation paths.
- **`COMPARISON`:** Contrasting policies, limits, or conditions.
- **`MULTI_HOP`:** Reasoning across multiple sentences, sections, or documents.
- **`NUMERICAL`:** Quantitative criteria, thresholds, currencies (e.g. AED limits), and durations.
- **`DOCUMENT_SPECIFIC`:** Identification of specific regulatory circulars, sections, or clauses.
- **`UNANSWERABLE`:** Negative cases designed to test appropriate refusal and hallucination avoidance.

### Deterministic Split Partitioning
Splits are deterministically assigned via SHA-256 hash modulo arithmetic:
$$\text{bucket} = \text{SHA256}(\text{case\_id}) \pmod{100}$$
- `bucket < 60`: **`DEVELOPMENT`** (60%)
- `60 <= bucket < 80`: **`VALIDATION`** (20%)
- `bucket >= 80`: **`HOLDOUT`** (20%)

---

## 5. Metric Evaluator Engine

The engine implements 11 deterministic metric evaluators:

| Metric | Scoring Method | Evaluation Purpose | Score Scale |
| :--- | :--- | :--- | :--- |
| **Exact Match** | Character/Token Identity | Normalizes punctuation/casing; assesses exact token parity. | 0.0 or 1.0 (0-100) |
| **Token F1** | Bag-of-Words Precision/Recall | Harmonic mean of token precision and recall against ground truth. | 0.0 to 1.0 (0-100) |
| **Keyword Coverage** | Set Recall | Checks presence of essential domain entities and keywords. | 0.0 to 1.0 (0-100) |
| **Retrieval Quality** | IR Ranking Metrics | Computes Precision@K, Recall@K, and Mean Reciprocal Rank (MRR). | 0.0 to 1.0 (0-100) |
| **Context Relevance** | Query-Chunk Relevance | Verifies retrieved chunks directly inform the question. | 0.0 to 1.0 (0-100) |
| **Groundedness** | Hallucination Guard | Verifies claims in answer are strictly supported by retrieved context. | 0.0 to 1.0 (0-100) |
| **Faithfulness** | Reference Consistency | Measures factual consistency between generated answer and ground truth. | 0.0 to 1.0 (0-100) |
| **Citation Verification** | Grounded Citation Links | Validates that cited documents and chunk indices exist and match claims. | 0.0 to 1.0 (0-100) |
| **Appropriate Abstention** | Negative Question Refusal | Detects refusal phrasing on unanswerable queries; penalizes hallucinated claims. | 0.0 to 1.0 (0-100) |
| **Safety** | Zero PII Leaks Guard | Scans actual output for raw phone numbers, emails, IBANs, or Emirates IDs. | 1.0 (Safe) or 0.0 |
| **Business Compliance** | Policy Invariants | Checks domain-specific mandatory disclosures and disallowed assertions. | 0.0 to 1.0 (0-100) |

---

## 6. Frontend Evaluation Centre

Located in `frontend/src/features/evaluation/`:
- **`EvaluationOverviewPage.tsx`**: Suite management, status indicators, quick stats, run summaries, and benchmark launcher.
- **`EvaluationSuiteDetailPage.tsx`**: Question inspection, category/difficulty filters, review action modal (Approve, Edit, Reject, Flag), Exam Generation modal, and immutable suite freeze action.
- **`EvaluationRunPage.tsx`**: Scorecard dashboard with 11-metric gauges, per-case result drilldown (actual answer vs expected answer, inline citations, latency), and report download triggers (JSON, Markdown, CSV).
- **Navigation & Routing**: Integrated into `frontend/src/app/App.tsx` under `/evaluation`, `/evaluation/suites/:suiteId`, and `/evaluation/runs/:runId`.
