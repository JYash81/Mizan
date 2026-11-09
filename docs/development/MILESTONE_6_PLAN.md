# MIZAN — MILESTONE 6 MASTER IMPLEMENTATION PLAN
## Build the Exam & Evaluation Engine: Automated Evaluation Suite Generation, Domain-Specific Question Generation, Scoring Rubrics, Groundedness, Faithfulness, Compliance and Benchmark Assessment

---

### 1. Executive Summary & Objective

Milestone 6 builds the core intelligence layer of Mizan: the **Exam & Evaluation Engine**. Mizan enables businesses to experiment with AI using their own approved business data by creating rigorous examinations derived from Gate 1 human-approved knowledge bases, evaluating multiple AI approaches using structured rubrics, and generating reproducible benchmark reports.

This plan adheres strictly to the **Free-Only Infrastructure Policy**: all processing, embeddings, vector queries, generation, evaluation, and report creation operate locally on CPU (Intel Core i5, 8 GB RAM, Windows 10) with **zero additional cost ($0.00)**, completely rejecting paid APIs, paid model judges, or external GPU clusters.

---

### 2. Verified Baseline (M1–M5)

- **Backend Pytest**: 112 passed (0 failures, 29.27s).
- **Backend Linter**: Ruff clean (0 errors).
- **Frontend Vitest**: 13 passed (0 failures, 7.85s).
- **Frontend Linter**: ESLint clean (0 errors, 0 warnings).
- **Frontend TypeScript**: `tsc -b` clean.
- **Frontend Build**: Production Vite bundle verified (`dist/index.html` 0.40 kB, `dist/assets/index-DEpkrNdO.js` 436.76 kB).
- **Alembic Database Head**: `20261108_0006_masking_and_gate1`.
- **Remote MySQL Concurrency Verification**: Preserved as `BLOCKED` in `docs/PROJECT_STATUS.md` without impeding local development.

---

### 3. Architecture & Domain Model

```
                    +--------------------------------------------+
                    | Gate 1 Approved Masked Dataset Version    |
                    | (StorageBucket.MASKED_DATASETS)            |
                    +---------------------+----------------------+
                                          |
                                          v  [require_gate1_approval()]
                    +--------------------------------------------+
                    | Evaluation Suite & Generation Service      |
                    | (Rule-Based, Mock, or Local Provider)      |
                    +---------------------+----------------------+
                                          |
               +--------------------------+--------------------------+
               |                                                     |
               v                                                     v
+-----------------------------+                       +-----------------------------+
| Evaluation Cases (Generated)|                       | Evaluation Rubric & Criteria|
| Types: Factual, Conceptual, |                       | Correctness, Relevance,     |
| Procedural, Comparison,     |                       | Groundedness, Faithfulness, |
| Multi-hop, Unanswerable     |                       | Citations, Abstention,      |
+--------------+--------------+                       | Safety, Compliance          |
               |                                      +--------------+--------------+
               v                                                     |
+-----------------------------+                                      |
| Human Review & Curation     |                                      |
| (Approve, Edit, Reject)     |                                      |
+--------------+--------------+                                      |
               |                                                     |
               v                                                     |
+----------------------------------------------------+               |
| Finalized Immutable Evaluation Suite Version       |               |
| (SHA-256 Digest, Dataset Provenance, Ed25519)     |<---------------+
+----------------------+-----------------------------+
                       |
                       v
+----------------------------------------------------+
| Evaluation Run Execution Engine                   |
| Target: M5 RAG Pipeline / Single Model / Responses|
+----------------------+-----------------------------+
                       |
                       v
+----------------------------------------------------+
| Deterministic CPU Evaluators (0-100 Normalized)   |
| Exact Match, Token F1, Recall@K, Relevance,        |
| Faithfulness, Citation Verification, Abstention   |
+----------------------+-----------------------------+
                       |
                       v
+----------------------------------------------------+
| Evaluation Results, Scorecard & Multi-Format Report|
| (JSON, Markdown, CSV, Frontend Evaluation Centre)  |
+----------------------------------------------------+
```

---

### 4. Implementation Phases

#### Phase 1: Audit & Baseline Verification
- Confirm 112 backend tests and 13 frontend tests pass. (COMPLETED)

#### Phase 2: Requirements Traceability & Master Plan
- Author `docs/development/MILESTONE_6_PLAN.md`. (ACTIVE)

#### Phase 3: Evaluation Domain Models
- Define SQLAlchemy models in `backend/app/models/evaluation.py`:
  - `EvaluationSuite`, `EvaluationSuiteStatus` (`DRAFT`, `GENERATING`, `REVIEW_REQUIRED`, `READY`, `ARCHIVED`).
  - `EvaluationSuiteVersion`, `SuiteVersionStatus` (`FINALIZED`, `ARCHIVED`).
  - `EvaluationCase`, `CaseCategory` (`FACTUAL`, `CONCEPTUAL`, `PROCEDURAL`, `COMPARISON`, `MULTI_HOP`, `NUMERICAL`, `DOCUMENT_SPECIFIC`, `UNANSWERABLE`), `DifficultyLevel` (`EASY`, `MEDIUM`, `HARD`, `MULTI_HOP`), `GroundTruthStatus` (`GENERATED`, `NEEDS_REVIEW`, `HUMAN_VERIFIED`, `REJECTED`, `ARCHIVED`), `SplitType` (`DEVELOPMENT`, `VALIDATION`, `HOLDOUT`).
  - `EvaluationRubric`, `RubricCriterion`, `ScoringMethod` (`EXACT_MATCH`, `TOKEN_F1`, `KEYWORD_COVERAGE`, `RETRIEVAL_METRIC`, `GROUNDEDNESS`, `FAITHFULNESS`, `CITATION_VERIFICATION`, `ABSTENTION`, `SAFETY`, `COMPLIANCE`).
  - `EvaluationRun`, `EvaluationRunStatus` (`DRAFT`, `QUEUED`, `RUNNING`, `EVALUATING`, `COMPLETED`, `FAILED`, `CANCELLED`).
  - `EvaluationCaseResult`, `EvaluationMetricResult`, `EvaluationReview`.

#### Phase 4: Database Migration
- Generate incremental Alembic migration `20261108_0007_evaluation_engine.py`.
- Apply migration to SQLite development database and verify schema integrity.

#### Phase 5: Suite & Case Repositories
- Implement repositories in `backend/app/modules/evaluation/repositories/` with strict workspace/tenant scoping.

#### Phase 6: Rule-Based & Mock Exam Generation
- Implement `RuleBasedExamGenerator` in `backend/app/modules/evaluation/generators/`:
  - Tokenizes and analyzes masked text from `StorageBucket.MASKED_DATASETS`.
  - Extracts key factual propositions and entity relations.
  - Synthesizes diverse categories: factual queries, procedural steps, numerical facts, conceptual summaries, and unanswerable queries (essential for testing hallucination and abstention).
  - Preserves exact source document IDs, chunk indices, and character offsets.
  - Computes deterministic split assignment (`DEVELOPMENT`, `VALIDATION`, `HOLDOUT`) using stable hashing.

#### Phase 7: Gate 1 Invariant Guard in Generation
- Strictly enforce `require_gate1_approval()` before generating any questions.
- Reject unapproved raw or unverified versions with HTTP 403 Forbidden.

#### Phase 8: Human Review Workflow & Manual Case Creation
- Review endpoints: `/approve`, `/reject`, `/edit` with audit history.
- Manual test case insertion with explicit `HUMAN_VERIFIED` status.

#### Phase 9: Immutable Suite Finalization
- Validate all cases, calculate canonical SHA-256 suite digest over sorted cases, bind to Gate 1 approval ID and dataset version ID.
- Freeze version against further edits.

#### Phase 10: Rubric Builder & Validation
- Default multi-dimensional rubric with configurable criterion weights (summing to 1.0 or normalized).

#### Phase 11: Deterministic Metric Evaluators
- `ExactMatchEvaluator`: Normalized string comparison.
- `TokenF1Evaluator`: Precision, Recall, F1 with language-aware tokenization.
- `KeywordCoverageEvaluator`: Essential keyword checking.
- `RetrievalEvaluator`: Precision@K, Recall@K, MRR.
- `ContextRelevanceEvaluator`: Query-context alignment.
- `FaithfulnessEvaluator`: Decomposes answer into claims, verifies supporting evidence in context.
- `GroundednessEvaluator`: Validates evidence chains and attribution.
- `CitationEvaluator`: Completeness and correctness check against retrieved chunks.
- `AbstentionEvaluator`: Rewards refusal on unanswerable questions, penalizes false refusals.
- `SafetyAndComplianceEvaluator`: Configured prohibited patterns and regulatory rules.

#### Phase 12: Evaluation Run Execution Engine
- `EvaluationService`: Executes a suite version against the M5 RAG pipeline or supplied responses.
- Evaluates each case across all rubric criteria, persists case and metric results, computes weighted overall score.

#### Phase 13: Report Generation (JSON, Markdown, CSV)
- Comprehensive multi-format reports with per-case breakdowns, metrics summaries, and limitation disclaimers.

#### Phase 14: REST API Endpoints & Permissions
- Suite CRUD, generation, review, finalization, rubric management, run execution, and report downloads.
- Tenant isolation and permission enforcement.

#### Phase 15: Frontend Evaluation Centre
- `frontend/src/features/evaluation/`:
  - Types and API client.
  - `EvaluationOverviewPage`: Dashboard with metrics, active suites, and runs.
  - `EvaluationSuiteDetailPage`: Question review table, approval actions, split badges, finalization button.
  - `ExamGenerationModal`: Generator parameters, difficulty distribution, Gate 1 verification badge.
  - `RubricManager`: Criterion weights editor.
  - `EvaluationRunPage`: Target selector, live execution progress, scorecard, and per-case inspector.
  - Report export viewer.
  - Wire routes in `App.tsx`.

#### Phase 16: Automated Backend & Frontend Tests
- Question generation tests (Gate 1 guard, categories, difficulties, unanswerable questions, Arabic/English).
- Rubric and normalization tests.
- Evaluator unit tests across all 11 metrics.
- Suite finalization and immutability tests.
- Full lifecycle integration tests (Generate -> Review -> Finalize -> Run -> Report).
- Tenant isolation tests.
- Frontend Vitest tests.

#### Phase 17: Quality Gates, Verification & Documentation
- Run Pytest, Ruff, Vitest, ESLint, TypeScript `tsc -b`, Vite production build.
- Produce `docs/development/MILESTONE_6_COMPLETION_REPORT.md` and update `docs/PROJECT_STATUS.md`.
