# Milestone 4 Completion Report: Sensitive Data Detection, Personal Information Masking, Data Protection Review & Gate 1 Human Approval

**Status:** COMPLETE & VERIFIED  
**Date:** 2026-11-08  
**Authoritative Baseline:** Mizan High-Level Design (`docs/reference/mizan_hld.png`) & Master Project Development Directive  
**Verified Environments:** Windows 10, Intel Core i5, 8 GB RAM, Python 3.12.10, Node.js 24.19.0

---

## 1. Executive Summary

Milestone 4 establishes the security-critical **Data Protection and Human In-the-Loop Governance Boundary** for Mizan: **Gate 1 — A person approves the masked sample**.

In strict accordance with the Mizan Product Invariants:
1. **Raw Business Data Sovereignty:** Original business documents in `StorageBucket.RAW_UPLOADS` are strictly isolated within the Workshop Data Plane and never leave the sovereign boundary.
2. **Outside Services Receive Only Masked Data:** External LLMs and pay-as-you-go GPU clouds are allowed to receive **ONLY** approved, masked text.
3. **Mandatory Human Gate 1:** An automated detection score, masking run, or hash does **NOT** constitute approval. An authorized human reviewer must inspect detections, review unmasked snippets in a controlled audit environment, make corrections, and execute a cryptographically signed **Gate 1 Approval Attestation (Ed25519)**.
4. **Zero-PII Metadata Invariant:** Raw personal identifiers are never stored in relational metadata, application logs, audit logs, or error responses. Unmasked previews are generated on-the-fly exclusively for authorized reviewers.
5. **OCR Safety Guard:** Documents with incomplete extraction or missing OCR strictly block Gate 1 approval unless explicitly excluded with recorded human rationale.

---

## 2. Key Deliverables & Architectural Components

### A. Presidio Analyzer & Localized UAE Recognizers (`app/modules/masking/recognizers/`)
- **UAE Emirates ID Recognizer (`UAE_EMIRATES_ID`):** Validates 15-digit sequences starting with `784` (UAE ISO numeric country code), handling formatted (`784-XXXX-XXXXXXX-X`), spaced, and unhyphenated inputs with word boundary checks.
- **UAE IBAN Recognizer (`UAE_IBAN`):** Validates 23-character strings starting with `AE` using algorithmic **ISO 13616 MOD-97** check-digit calculation ($(\text{rearranged integer}) \pmod{97} == 1$).
- **UAE Telephone Recognizer (`UAE_PHONE_NUMBER`):** Integrates Google's `phonenumbers` library configured for region `"AE"`, enforcing TDRA mobile allocations (`050`, `052`, `054`, `055`, `056`, `058`) and landlines (`02`, `04`, `06`, `07`, `09`).
- **Resource-Constrained Spacy NLP Engine:** Uses lightweight blank spaCy pipelines fallback without downloading 400 MB packages, keeping the system responsive on 8 GB RAM machines while fully detecting pattern entities.

### B. Unicode Code-Point Offsets & Overlap Resolution (`app/modules/masking/services/offset_service.py`)
- Standardized character-level Unicode code-point indexing (`0 <= start < end <= text_length`).
- Transitive connected-component graph clustering for overlapping detections (`overlap_group_id`).
- Merging overlapping intervals into minimal disjoint sets.
- Strict descending-offset replacement sorting to prevent string offset drift during masking transformations.

### C. Deterministic Masking Engine (`app/modules/masking/services/masking_service.py`)
- Three masking strategies:
  - `REPLACE_WITH_ENTITY_LABEL`: Default strategy replacing spans with bracketed entity tags (`[UAE_EMIRATES_ID]`, `[UAE_IBAN]`, etc.).
  - `REDACT`: Uniform blackout block (`[REDACTED]`).
  - `PARTIAL_MASK`: Preserves non-sensitive structural portions (e.g. `784-1985-XXXXXXX-1`, `AE14...0000`, `us***@mizan.ae`).
- Precedence-based conflict resolution for overlapping spans (e.g. `UAE_EMIRATES_ID` > general number).
- Immutable masked artifacts stored in `StorageBucket.MASKED_DATASETS`.
- Permanent SHA-256 digest computation recorded in `MaskingRun.masked_output_digest`.

### D. Relational Models & Alembic Migration (`20261108_0006_masking_and_gate1.py`)
- `MaskingProfile`: Configurable masking strategies and enabled entity sets.
- `MaskingRun`: Tracks batch detection, extraction coverage, processed counts, and output digest.
- `PiiFinding`: Relational finding record storing offsets, scores, and entity types (**zero raw PII**).
- `MaskingDecision`: Human reviewer actions (`CONFIRMED`, `FALSE_POSITIVE`, `CUSTOM_REPLACEMENT`).
- `Gate1Approval`: Digital approval attestation storing Ed25519 signature and canonical payload.
- `Gate1ApprovalEvent`: Audit trail of approval lifecycle events.

### E. Ed25519 Cryptographic Attestation & Downstream Guard
- `signing_service.py`: Generates and loads Ed25519 private keys stored outside Git (`storage/keys/`).
- Canonical JSON serialization with sorted keys, compact separators, and ISO 8601 UTC timestamps.
- `verify_gate1_approval()`: Verifies digital signatures and detects tampering or source dataset modification.
- `require_gate1_approval()`: Centralized reusable guard for downstream milestones (RAG and Experiments), failing closed with HTTP 403 if Gate 1 approval is missing or unverified.

### F. REST APIs (`app/api/v1/endpoints/masking.py` & `gate1.py`)
- `/api/v1/workspaces/{workspace_id}/masking-profiles` (CRUD)
- `/api/v1/workspaces/{workspace_id}/masking-runs` (Execute detection & masking)
- `/api/v1/workspaces/{workspace_id}/masking-runs/{run_id}/findings` (List detections)
- `/api/v1/workspaces/{workspace_id}/masking-runs/{run_id}/findings/manual` (Add manual PII spans)
- `/api/v1/workspaces/{workspace_id}/masking-runs/{run_id}/findings/{finding_id}/decisions` (Review dispositions)
- `/api/v1/workspaces/{workspace_id}/masking-runs/{run_id}/documents/{doc_id}/review` (Side-by-side review content)
- `/api/v1/workspaces/{workspace_id}/masking-runs/{run_id}/gate1/approve` (Cryptographic approval)
- `/api/v1/workspaces/{workspace_id}/masking-runs/{run_id}/gate1/reject` (Rejection)
- `/api/v1/workspaces/{workspace_id}/gate1/approvals/{approval_id}/verify` (Signature verification)

### G. Frontend Data Protection Workspace (`frontend/src/features/data-protection/`)
- `DataProtectionOverviewPage`: Metrics cards, masking runs list, extraction coverage badges, and Gate 1 status pills.
- `MaskingReviewPage`: Split-pane reviewer interface (original document with highlighted spans vs live masked preview), findings disposition buttons, and manual span addition.
- `Gate1ApprovalModal`: Checkpoint verification modal displaying digest fingerprints, role snapshots, OCR warning override inputs, and digital signing action.

---

## 3. Test Evidence & Quality Verification

| Test Suite / Tool | Scope | Result | Details |
| :--- | :--- | :--- | :--- |
| **Pytest Backend** | Complete Backend Suite | **93 PASSED** | 0 failures in 19.07s (`tests/test_*.py`) |
| **Pytest UAE Recognizers** | Emirates ID, IBAN MOD-97, Phone | **4 PASSED** | `test_uae_recognizers.py` |
| **Pytest Offsets & Overlaps** | Boundaries, Overlaps, Arabic/Emoji | **6 PASSED** | `test_offsets_and_overlaps.py` |
| **Pytest Masking Engine** | Strategies, Overlaps, Digests | **6 PASSED** | `test_masking_service.py` |
| **Pytest Ed25519 Attestation** | Canonical JSON, Tamper Detection | **4 PASSED** | `test_ed25519_attestation.py` |
| **Pytest Gate 1 API & Guards** | Full Lifecycle, OCR Guard, RBAC | **2 PASSED** | `test_gate1_api.py` |
| **Pytest Tenant Isolation** | Cross-Tenant Anti-Enumeration (404) | **1 PASSED** | `test_masking_tenant_isolation.py` |
| **Ruff Linter & Formatter** | Python 3.12 Backend | **CLEAN** | 0 warnings, 0 errors |
| **Alembic Migration** | Database Schema Upgrade | **HEAD** | `20261108_0006_masking_and_gate1` |
| **Vitest Frontend** | React Testing Library | **9 PASSED** | 0 failures in 5.20s |
| **ESLint** | Frontend TypeScript / React | **CLEAN** | 0 warnings, 0 errors |
| **TypeScript Compiler** | `tsc --noEmit` Strict Mode | **CLEAN** | 0 type errors |
| **Vite Production Build** | Production Asset Compilation | **SUCCESS** | Bundled in 6.59s to `frontend/dist/` |

---

## 4. Invariant Verification

- [x] **Raw Business Data Sovereignty:** Original unmasked documents never leave `StorageBucket.RAW_UPLOADS`.
- [x] **No Unapproved Data in Experimentation:** `require_gate1_approval()` strictly denies external access (HTTP 403) unless an Ed25519 signed approval exists and verifies.
- [x] **Zero Raw PII in Relational Metadata:** Database tables store entity types, scores, offsets, and digest references, but never raw detected personal data.
- [x] **OCR Safety Guard:** Documents with incomplete extraction or missing OCR block Gate 1 approval unless explicitly excluded with recorded justification.
- [x] **Multi-Tenant Anti-Enumeration:** Cross-tenant masking run or approval requests return HTTP 404.
