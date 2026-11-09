# Mizan Dataset and Document Schema Specification

**Database:** Metadata Store (SQLite local / Hostinger MySQL production)  
**Migration:** `20261108_0005_datasets_and_documents`  
**Updated:** 2026-11-08  

---

## 1. Relational Entity-Relationship Model

```
                    ┌────────────────────────┐
                    │      workspaces        │
                    └───────────┬────────────┘
                                │ 1:N
                    ┌───────────▼────────────┐
                    │        datasets        │
                    └───────────┬────────────┘
                                │ 1:N
                    ┌───────────▼────────────┐
                    │    dataset_versions    │
                    └─────┬────────────┬─────┘
                      1:N │            │ 1:N
      ┌───────────────────▼───┐    ┌───▼───────────────────┐
      │       documents       │    │    processing_jobs    │
      └───────────────────────┘    └───────────────────────┘
```

---

## 2. Table Specifications

### A. `datasets`
Represents a logical grouping of business documentation and training material (e.g. "HR Policy Manuals", "Retail Onboarding FAQs").

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(36) | PRIMARY KEY | UUID v4 string. |
| `workspace_id` | VARCHAR(36) | NOT NULL, FK(`workspaces.id`, CASCADE) | Workspace tenant owner. |
| `name` | VARCHAR(120) | NOT NULL | Human-readable dataset name. |
| `slug` | VARCHAR(120) | NOT NULL | URL-safe slug within workspace. |
| `description` | TEXT | NULLABLE | Detailed description of contents. |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'ACTIVE' | `ACTIVE`, `ARCHIVED`. |
| `created_by_id` | VARCHAR(36) | NOT NULL, FK(`users.id`) | Creator user identifier. |
| `created_at` | DATETIME | NOT NULL | Creation timestamp (UTC). |
| `updated_at` | DATETIME | NOT NULL | Last update timestamp (UTC). |

*Indexes & Constraints:*
- `uq_datasets_workspace_slug`: UNIQUE (`workspace_id`, `slug`).
- `ix_datasets_workspace_id`: INDEX (`workspace_id`).

---

### B. `dataset_versions`
Represents an immutable snapshot of a dataset. When documents are added or updated, a new version is created. Experimentation and Gate 1 approvals bind to a specific version.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(36) | PRIMARY KEY | UUID v4 string. |
| `dataset_id` | VARCHAR(36) | NOT NULL, FK(`datasets.id`, CASCADE) | Parent dataset. |
| `version_number` | INTEGER | NOT NULL | Sequential integer (1, 2, 3...). |
| `name` | VARCHAR(64) | NOT NULL | Version label (e.g. `v1`). |
| `description` | TEXT | NULLABLE | Version changelog/notes. |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'DRAFT' | `DRAFT`, `PROCESSING`, `READY`, `ARCHIVED`. |
| `total_documents` | INTEGER | NOT NULL, DEFAULT 0 | Count of documents in version. |
| `total_raw_bytes` | BIGINT | NOT NULL, DEFAULT 0 | Sum of raw document byte sizes. |
| `content_hash` | VARCHAR(64) | NULLABLE | Aggregated SHA-256 digest of version. |
| `created_at` | DATETIME | NOT NULL | Creation timestamp (UTC). |
| `updated_at` | DATETIME | NOT NULL | Last update timestamp (UTC). |

*Indexes & Constraints:*
- `uq_dataset_versions_dataset_num`: UNIQUE (`dataset_id`, `version_number`).
- `ix_dataset_versions_dataset_id`: INDEX (`dataset_id`).

---

### C. `documents`
Represents an individual uploaded business file and its extracted text and structural metadata.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(36) | PRIMARY KEY | UUID v4 string. |
| `dataset_version_id`| VARCHAR(36) | NOT NULL, FK(`dataset_versions.id`, CASCADE) | Target version. |
| `workspace_id` | VARCHAR(36) | NOT NULL, FK(`workspaces.id`, CASCADE) | Redundant tenant index for fast querying. |
| `name` | VARCHAR(255) | NOT NULL | Original sanitized filename. |
| `file_type` | VARCHAR(32) | NOT NULL | `PDF`, `DOCX`, `TXT`, `CSV`, `XLSX`, `JSON`, `JSONL`, `IMAGE`. |
| `mime_type` | VARCHAR(120) | NOT NULL | Validated MIME type. |
| `raw_file_key` | VARCHAR(512) | NOT NULL | Storage key in `raw_uploads` bucket. |
| `raw_file_size_bytes` | BIGINT | NOT NULL | File size in bytes. |
| `raw_sha256` | VARCHAR(64) | NOT NULL | Content cryptographic checksum. |
| `extracted_text_key` | VARCHAR(512) | NULLABLE | Storage key for full extracted text. |
| `extracted_text_sample` | TEXT | NULLABLE | Truncated preview (first 1,000 characters). |
| `char_count` | INTEGER | NOT NULL, DEFAULT 0 | Extracted character count. |
| `word_count` | INTEGER | NOT NULL, DEFAULT 0 | Extracted word count. |
| `page_count` | INTEGER | NULLABLE | Page count (for PDF / DOCX). |
| `extraction_status` | VARCHAR(32) | NOT NULL, DEFAULT 'PENDING' | `PENDING`, `PARSING`, `COMPLETED`, `FAILED`. |
| `extraction_error` | TEXT | NULLABLE | Error message if parsing failed. |
| `created_at` | DATETIME | NOT NULL | Creation timestamp (UTC). |
| `updated_at` | DATETIME | NOT NULL | Last update timestamp (UTC). |

*Indexes & Constraints:*
- `ix_documents_dataset_version`: INDEX (`dataset_version_id`).
- `ix_documents_workspace_id`: INDEX (`workspace_id`).
- `ix_documents_raw_sha256`: INDEX (`raw_sha256`).

---

### D. `processing_jobs`
Database-backed job ledger for tracking asynchronous document extraction and version snapshot compilation.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(36) | PRIMARY KEY | UUID v4 string. |
| `workspace_id` | VARCHAR(36) | NOT NULL, FK(`workspaces.id`, CASCADE) | Tenant owner. |
| `dataset_version_id`| VARCHAR(36) | NULLABLE, FK(`dataset_versions.id`, SET NULL) | Associated dataset version. |
| `document_id` | VARCHAR(36) | NULLABLE, FK(`documents.id`, CASCADE) | Associated document. |
| `job_type` | VARCHAR(64) | NOT NULL | `DOCUMENT_EXTRACTION`, `VERSION_COMPILATION`. |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'PENDING' | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`. |
| `progress_pct` | INTEGER | NOT NULL, DEFAULT 0 | Progress percentage (0–100). |
| `error_message` | TEXT | NULLABLE | Error details if failed. |
| `started_at` | DATETIME | NULLABLE | Execution start timestamp. |
| `completed_at` | DATETIME | NULLABLE | Execution completion timestamp. |
| `created_at` | DATETIME | NOT NULL | Creation timestamp (UTC). |
| `updated_at` | DATETIME | NOT NULL | Last update timestamp (UTC). |

*Indexes & Constraints:*
- `ix_processing_jobs_workspace_id`: INDEX (`workspace_id`).
- `ix_processing_jobs_status`: INDEX (`status`).
