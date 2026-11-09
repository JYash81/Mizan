# Milestone 4 Implementation Plan: Sensitive Data Detection, Masking, Review & Gate 1 Human Approval

**Project:** MIZAN — Enterprise AI Experimentation, Evaluation & Distribution Platform  
**Milestone:** 4 — Data Protection, Personal Information Masking, and Gate 1 Approval  
**Status:** IN PROGRESS  
**Date:** 2026-11-08  
**Author:** Principal Software Architect, Application Security Engineer & Engineering Team  

---

## 1. Objective and Invariant

### Core Objective
Implement the comprehensive **Data Protection and Masking — Gate 1** subsystem in Mizan's Data Plane Workshop, ensuring that no uploaded raw business document can enter the external AI experimentation or teacher LLM pipeline without automated PII detection, structured finding extraction, deterministic masking, human review, cryptographic digest calculation, and an explicit, verifiable **Gate 1 Human Approval Attestation**.

### Mandatory Invariant
> **NO UNAPPROVED RAW OR MASKED DATASET MAY ENTER THE EXTERNAL EXPERIMENTATION PIPELINE.**  
> An automated detector result is NOT human approval.  
> A successful masking run is NOT human approval.  
> An artifact hash is NOT human approval.  
> An authorized human reviewer must inspect the findings and explicitly approve the finalized masked dataset version.

---

## 2. Architectural Blueprint

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATASET VERSION READY (FROM MILESTONE 3)                 │
│         Immutable snapshot with cumulative SHA-256 digest in Storage        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Trigger Masking Run
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PRESIDIO PII DETECTION ENGINE                         │
│  - Microsoft Presidio Analyzer                                              │
│  - Built-in Recognizers: EMAIL, PHONE, PERSON, LOCATION, CREDIT_CARD, IBAN   │
│  - Custom UAE Recognizers:                                                  │
│    * UAE_EMIRATES_ID (784-XXXX-XXXXXXX-X, structural & regex validation)    │
│    * UAE_IBAN (23 chars, AE prefix, ISO 13616 MOD-97 checksum validation)   │
│    * UAE_PHONE_NUMBER (TDRA ranges: 050, 052, 054, 055, 056, 058, +971)     │
│  - Extraction Coverage Guard (Blocks scanned/empty PDFs & image-only docs)  │
│  - Unicode Code-Point Offsets & Overlap Resolution                          │
└──────────────────┬───────────────────────────────────────────┬──────────────┘
                   │ Store Findings (No Raw PII in DB)         │ Stream Text
                   ▼                                           ▼
┌─────────────────────────────────────────┐   ┌───────────────────────────────┐
│        METADATA STORE (DB)              │   │     DETERMINISTIC MASKING     │
│  - masking_profiles                     │   │  - REDACT                     │
│  - masking_runs                         │   │  - REPLACE_WITH_ENTITY_LABEL  │
│  - pii_findings                         │   │  - PARTIAL_MASK               │
│  - masking_decisions                    │   │  - Compute Masked Digest      │
└──────────────────┬──────────────────────┘   └───────────────┬───────────────┘
                   │                                          │ Store Masked Doc
                   ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 DATA PROTECTION REVIEW WORKSPACE (WEB CONSOLE)              │
│  - Authorized DPO / Reviewer inspects side-by-side original vs masked       │
│  - Audited access to unmasked source snippets                               │
│  - Actions: Confirm, False Positive, Edit Span, Add Manual Finding          │
│  - Rebuild Masked Output & Recalculate Digest                               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Human Review Decision
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GATE 1 HUMAN APPROVAL WORKFLOW                        │
│  - Re-verify source digest, output digest, coverage, unresolved conflicts   │
│  - Human Approver binds identity + role + decision reason                   │
│  - Platform Ed25519 Signing Service creates immutable attestation           │
│  - Gate 1 Guard: Fail-closed gate for all downstream experiment engines     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Phase Breakdown

### Phase 1: Repository Audit and Milestone 3 Verification
- Confirm 70 backend Pytest tests, 5 frontend Vitest tests, Ruff, ESLint, and Vite build baselines.
- Verify migration head `20261108_0005_datasets_and_documents`.

### Phase 2: Presidio Dependency & Configuration
- Install `presidio-analyzer`, `phonenumbers`, and `cryptography` in `backend/.venv` and pin in `requirements.txt`.
- Configure CPU-friendly lightweight NLP settings (no heavy downloads on 8 GB RAM local environment).

### Phase 3: Recognizer Registry
- Create `backend/app/modules/masking/recognizers/registry.py`:
  - Centralized registry initializing Presidio `AnalyzerEngine`.
  - Registration of default entities and custom UAE patterns.
  - Multi-language profile management (English, Arabic).

### Phase 4: UAE Emirates ID Recognizer
- `backend/app/modules/masking/recognizers/emirates_id.py`:
  - Authoritative reference: UAE Government Design System (`784-XXXX-XXXXXXX-X`).
  - Regex pattern matching 15-digit structure with prefix `784`.
  - Format variation support (with/without hyphens, spaces).
  - Masked display helper (`784-1945-XXXXXXX-X`).

### Phase 5: UAE IBAN Recognizer
- `backend/app/modules/masking/recognizers/uae_iban.py`:
  - Authoritative reference: Central Bank of the UAE & ISO 13616.
  - Structure: 23 characters (`AE` + 2 check digits + 3 bank code + 16 account digits).
  - ISO 13616 MOD-97 checksum validation.

### Phase 6: UAE Telephone Recognizer
- `backend/app/modules/masking/recognizers/uae_phone.py`:
  - Authoritative reference: TDRA (Telecommunications and Digital Government Regulatory Authority).
  - Supported ranges: `050`, `052`, `054`, `055`, `056`, `058` mobile prefixes; national (`05X XXXXXXX`) and international (`+971 5X XXXXXXX`) formats.
  - Integration with `phonenumbers` regional parser.

### Phase 7: Person Name & Multilingual Recognition
- `backend/app/modules/masking/recognizers/person.py`:
  - English person recognition with lightweight context words and fallback rules.
  - Explicit documentation of Arabic NLP limitations on local hardware; support for manual finding additions.

### Phase 8: Unicode Code-Point Offset Tracking & Overlap Resolution
- `backend/app/modules/masking/services/offset_service.py`:
  - Canonical 0-based Unicode code point offsets (`start` inclusive, `end` exclusive).
  - Robust boundary validation: `0 <= start < end <= len(text)`.
  - Deterministic overlap grouping (`overlap_group_id`).
  - Descending-offset replacement algorithm to preserve coordinate integrity.

### Phase 9: PII Findings Schema & Database Models
- `backend/app/models/masking.py`:
  - `MaskingProfile`, `MaskingRun`, `PiiFinding`, `MaskingDecision`, `Gate1Approval`, `Gate1ApprovalEvent`.
  - Zero raw PII in database metadata fields.
  - Incremental Alembic migration: `20261108_0006_masking_and_gate1.py`.

### Phase 10: Masking Engine
- `backend/app/modules/masking/services/masking_service.py`:
  - Strategies: `REDACT`, `REPLACE_WITH_ENTITY_LABEL`, `PARTIAL_MASK`.
  - Deterministic string transformation and applied mask logging.
  - SHA-256 output digest generation.

### Phase 11: Storage Integration & Partitioning
- Persisting masked artifacts in `StorageBucket.MASKED_DATASETS`.
- Ensuring raw source files in `StorageBucket.RAW_UPLOADS` remain immutable.

### Phase 12: Detection & Masking Job Dispatcher
- `backend/app/modules/masking/services/detection_service.py`:
  - Batch document analysis.
  - Extraction coverage status evaluation (`EXTRACTION_COMPLETE`, `OCR_REQUIRED`, `EXTRACTION_FAILED`).
  - Safe failure trapping without crashing pipeline.

### Phase 13: Data Protection Review REST APIs
- `backend/app/api/v1/endpoints/masking.py`:
  - Masking run creation, findings listing, document review content, manual finding submission, output rebuilding.
- `backend/app/api/v1/endpoints/gate1.py`:
  - Gate 1 approval, rejection, and cryptographic verification endpoints.

### Phase 14: Centralized RBAC & Multi-Tenant Isolation
- New permissions: `DATASET_MASKING_READ`, `DATASET_MASKING_ANALYZE`, `DATASET_MASKING_REVIEW`, `DATASET_MASKING_MODIFY`, `DATASET_MASKING_APPROVE`.
- Anti-enumeration 404 enforcement for unauthorized tenants.

### Phase 15: Ed25519 Cryptographic Signing & Verification
- `backend/app/modules/masking/cryptography/signing_service.py`:
  - Canonical JSON serialization (sorted keys, compact separators, stable timestamps).
  - Ed25519 digital signature generation and tamper verification.
  - Development key management (stored outside Git).

### Phase 16: Centralized Gate 1 Enforcement Guard
- `backend/app/modules/masking/approval/gate1_service.py`:
  - Reusable `require_gate1_approval()` guard for downstream experiment runners.
  - Fail-closed security posture.

### Phase 17: Frontend Data Protection Review Workspace
- `frontend/src/features/data-protection/`:
  - Overview / Dashboard with real metrics.
  - Split-pane review interface (source with highlighted spans vs masked preview).
  - Action buttons: Confirm finding, False positive, Edit span, Add manual finding.
  - Gate 1 Approval Dialog with cryptographic signature verification badge.

### Phase 18: Automated Unit & Integration Testing
- UAE recognizer test suite (`test_uae_recognizers.py`).
- Unicode offsets & overlap test suite (`test_offsets_and_overlaps.py`).
- Masking engine determinism test suite (`test_masking_service.py`).
- Extraction coverage test suite (`test_extraction_coverage.py`).
- Ed25519 signing and tamper-resistance test suite (`test_ed25519_attestation.py`).
- Gate 1 approval lifecycle & API test suite (`test_gate1_api.py`).
- Tenant isolation & anti-enumeration test suite (`test_masking_tenant_isolation.py`).

### Phase 19: Full Regression Suite Verification
- Pytest, Ruff, Vitest, ESLint, TypeScript check, and production Vite build.

### Phase 20: Comprehensive Documentation & Milestone Report
- Complete architectural specifications and `MILESTONE_4_COMPLETION_REPORT.md`.
