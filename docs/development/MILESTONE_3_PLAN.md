# Milestone 3 Implementation Plan: Document & Data Management

**Project:** MIZAN — Enterprise AI Experimentation, Evaluation & Distribution Platform  
**Milestone:** 3 — Document Ingestion, Storage Abstraction, and Data Management  
**Status:** IN PROGRESS  
**Date:** 2026-11-08  
**Author:** Principal Software Architect & Engineering Team  

---

## 1. Objective and Scope

Milestone 3 implements the foundational **Data Plane — Workshop** storage and document ingestion subsystems as mandated by the authoritative High-Level Design (`docs/reference/mizan_hld.png`) and Master Project Development Directive:
1. **Storage Provider Abstraction:** A decoupled storage interface supporting private local filesystem storage in development and private S3-compatible / Cloudflare R2 object storage in staging/production, partitioned into 6 logical isolation buckets.
2. **File Safety and Content Validation:** Robust file integrity guards: 25 MB max upload limits, magic-byte inspection (not relying on file extensions), MIME type cross-validation, decompression-bomb defense for archive-based formats (DOCX/XLSX), path-traversal mitigation, and SHA-256 duplicate detection.
3. **Database Entities:** Schema models for `Dataset`, `DatasetVersion`, `Document`, and `ProcessingJob` with UUID primary keys, strict workspace-level tenant isolation, and audit timestamps.
4. **Bounded Document Text Parsers:** Resilient, pure-Python parsers for PDF (`pypdf`), DOCX (`python-docx`), XLSX (`openpyxl`), CSV, TXT/Markdown, JSON/JSONL, and Image metadata (`pillow`), with bounded execution timeouts and graceful failure handling.
5. **Backend Data Services & REST APIs:** Complete CRUD endpoints for datasets, dataset versions, multi-part document uploads, asynchronous extraction job tracking, safe document previews, and document deletion under strict RBAC.
6. **Interactive Frontend Experience:** Dedicated Datasets view, dataset detail workspace, drag-and-drop file upload dropzone with real-time feedback, processing status monitors, and document preview modals.
7. **Full Automated Verification:** Comprehensive unit and integration test suites validating storage operations, parser bounds, anti-traversal defenses, cross-tenant isolation, and frontend rendering.

---

## 2. Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND / CLIENT BROWSER                          │
│   (Upload dropzone, dataset explorer, processing monitors, preview modal)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Multipart POST /api/v1/workspaces/{ws_id}/...
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI CONTROL PLANE & INGESTION                        │
│   - Tenant resolution & RBAC (require DATASETS_CREATE / DOCUMENTS_UPLOAD)   │
│   - FileValidator: Size <= 25MB, Magic bytes check, Decompression bomb guard│
│   - SHA-256 computation & duplicate detection                                │
└──────────────────┬───────────────────────────────────────────┬──────────────┘
                   │ Store Raw Binary                          │ Record Metadata
                   ▼                                           ▼
┌─────────────────────────────────────────┐   ┌───────────────────────────────┐
│       STORAGE ABSTRACTION LAYER         │   │        METADATA STORE         │
│  - StorageBucket.RAW_UPLOADS            │   │  - datasets                   │
│  - LocalStorageProvider (dev disk)      │   │  - dataset_versions           │
│  - S3StorageProvider (prod S3/R2)       │   │  - documents                  │
│  - Strict Path Containment              │   │  - processing_jobs            │
└──────────────────┬──────────────────────┘   └───────────────┬───────────────┘
                   │ Pass byte stream                         │ Job state
                   ▼                                          │
┌─────────────────────────────────────────────────────────────┼───────────────┐
│               BOUNDED TEXT PARSER DISPATCHER                │               │
│  - PDF (pypdf), DOCX (docx), XLSX (openpyxl), CSV, TXT, JSON│               │
│  - Extract text sample, word count, character count, pages  │               │
│  - Transition ProcessingJob: PENDING -> RUNNING -> COMPLETED/FAILED         │
└─────────────────────────────────────────────────────────────┴───────────────┘
```

---

## 3. Implementation Phases

### Phase 1: Specifications & Architectural Design
- `docs/development/MILESTONE_3_PLAN.md` (this file)
- `docs/architecture/STORAGE_ARCHITECTURE.md`
- `docs/database/DATASET_AND_DOCUMENT_SCHEMA.md`
- `docs/security/DOCUMENT_INGESTION_SECURITY.md`

### Phase 2: Storage Abstraction Layer
- `backend/app/modules/storage/provider.py`: Base abstract class `StorageProvider`, `StorageObjectMetadata`, `StorageBucket` enum.
- `backend/app/modules/storage/local.py`: `LocalStorageProvider` with path-traversal prevention, atomic temp-file writes, SHA-256 calculation.
- `backend/app/modules/storage/s3.py`: `S3StorageProvider` interface for production S3/R2 with safe credentials check.
- `backend/app/modules/storage/service.py`: Centralized singleton factory returning active provider based on `Settings`.

### Phase 3: File Validation & Decompression Bomb Defenses
- `backend/app/modules/documents/services/file_validator.py`:
  - `validate_file_upload(filename, content, max_size_bytes)`:
  - Magic-byte validation table (PDF, ZIP/DOCX/XLSX, PNG, JPEG, WEBP, Plaintext).
  - Decompression bomb check for zip containers (inspect uncompressed ratio <= 100:1 and total uncompressed bytes <= 100MB).
  - Null malware scanner interface (`MalwareScanner`, `NullMalwareScanner`).

### Phase 4: Database Models & Alembic Migration
- `backend/app/models/dataset.py`:
  - `Dataset`, `DatasetVersion`, `Document`, `ProcessingJob`, `DatasetStatus`, `DatasetVersionStatus`, `DocumentFileType`, `ExtractionStatus`, `JobType`, `JobStatus`.
- Update `backend/app/models/__init__.py`.
- Alembic migration `20261108_0005_datasets_and_documents.py`.
- Run `alembic upgrade head`.

### Phase 5: Bounded Document Parsers
- `backend/app/modules/documents/parsers/`:
  - `base.py`: `BaseParser`, `ExtractedDocumentResult`.
  - `text.py`: TXT, Markdown, code, logs.
  - `tabular.py`: CSV, TSV, XLSX.
  - `json_parser.py`: JSON, JSONL.
  - `pdf.py`: PDF parser with page extraction and limits.
  - `docx_parser.py`: DOCX parser for paragraphs and tables.
  - `image.py`: Image metadata extractor.
  - `dispatcher.py`: Dynamic dispatch with error containment.

### Phase 6: Document & Dataset Backend Services
- `backend/app/modules/datasets/services/dataset_service.py`
- `backend/app/modules/documents/services/document_service.py`
- `backend/app/modules/documents/services/job_service.py`

### Phase 7: REST Endpoints & RBAC Integration
- Update `WorkspacePermission` with dataset & document permissions.
- `backend/app/api/v1/endpoints/datasets.py`
- `backend/app/api/v1/endpoints/documents.py`
- Register endpoints in `backend/app/api/v1/router.py`.

### Phase 8: Frontend Datasets & Document Management Experience
- `frontend/src/features/datasets/types.ts`
- `frontend/src/features/datasets/pages/DatasetsPage.tsx`
- `frontend/src/features/datasets/pages/DatasetDetailPage.tsx`
- `frontend/src/features/datasets/components/UploadDropzone.tsx`
- `frontend/src/features/datasets/components/DocumentPreviewModal.tsx`
- Connect `/datasets` route in `frontend/src/app/App.tsx`.

### Phase 9: Automated Test Suites & Regression Verification
- Storage provider tests (`test_storage_service.py`)
- File validator and parser tests (`test_file_validation_and_parsers.py`)
- Dataset schema and migration tests (`test_dataset_schema.py`)
- Dataset & Document API tests (`test_datasets_and_documents_api.py`)
- Tenant isolation tests (`test_dataset_tenant_isolation.py`)
- Frontend unit tests and build verification (`vitest`, `eslint`, `vite build`).

### Phase 10: Documentation & Milestone Completion Report
- `docs/development/MILESTONE_3_COMPLETION_REPORT.md`
- Update `docs/PROJECT_STATUS.md` and `docs/architecture/ARCHITECTURE_DECISION_RECORDS.md`.
