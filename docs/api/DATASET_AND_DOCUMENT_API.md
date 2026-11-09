# Mizan Dataset and Document API Reference

**Base Path:** `/api/v1`  
**Authentication:** HttpOnly Session Cookie (`mizan_session`) or Bearer Token  
**CSRF Protection:** State-changing requests (`POST`, `PATCH`, `DELETE`) require `X-CSRF-Token` header.  
**Multi-Tenant Guard:** All workspace endpoints enforce tenant boundary checks and anti-enumeration 404 responses.  

---

## 1. Datasets API

### Create Dataset
Creates a new dataset container within a workspace and initializes version 1 in `DRAFT` status.
- **Method:** `POST`
- **Path:** `/api/v1/workspaces/{workspace_id}/datasets`
- **Permission Required:** `workspace.datasets.create`
- **Request Body:**
  ```json
  {
    "name": "HR Global Policies",
    "slug": "hr-policies",
    "description": "Employee onboarding documentation and benefits handbooks"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "dataset": {
      "id": "e4b2d56a-1123-4567-89ab-cdef01234567",
      "workspace_id": "c9a29e4b-09e4-4c6e-8ff4-93452077e682",
      "name": "HR Global Policies",
      "slug": "hr-policies",
      "description": "Employee onboarding documentation and benefits handbooks",
      "status": "ACTIVE",
      "created_by": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "created_at": "2026-11-08T18:00:00Z",
      "updated_at": "2026-11-08T18:00:00Z",
      "active_version": null
    },
    "version": {
      "id": "f5c3e67b-2234-5678-90bc-def012345678",
      "dataset_id": "e4b2d56a-1123-4567-89ab-cdef01234567",
      "version_number": 1,
      "name": "v1",
      "description": "Initial dataset version",
      "status": "DRAFT",
      "total_documents": 0,
      "total_raw_bytes": 0,
      "content_hash": null,
      "created_at": "2026-11-08T18:00:00Z",
      "updated_at": "2026-11-08T18:00:00Z"
    }
  }
  ```

---

### List Datasets
Retrieves all datasets within a workspace with active version summaries.
- **Method:** `GET`
- **Path:** `/api/v1/workspaces/{workspace_id}/datasets?include_archived=false`
- **Permission Required:** `workspace.datasets.read`
- **Response (200 OK):**
  ```json
  {
    "datasets": [
      {
        "id": "e4b2d56a-1123-4567-89ab-cdef01234567",
        "workspace_id": "c9a29e4b-09e4-4c6e-8ff4-93452077e682",
        "name": "HR Global Policies",
        "slug": "hr-policies",
        "status": "ACTIVE",
        "active_version": {
          "id": "f5c3e67b-2234-5678-90bc-def012345678",
          "version_number": 1,
          "name": "v1",
          "status": "READY",
          "total_documents": 14,
          "total_raw_bytes": 4829104
        }
      }
    ]
  }
  ```

---

### Finalize Dataset Version (Freeze for Gate 1)
Aggregates all document content hashes, computes the cumulative SHA-256 version digest, and transitions status from `DRAFT` to `READY`.
- **Method:** `POST`
- **Path:** `/api/v1/workspaces/{workspace_id}/datasets/{dataset_id}/versions/{version_id}/finalize`
- **Permission Required:** `workspace.datasets.update`
- **Response (200 OK):**
  ```json
  {
    "version": {
      "id": "f5c3e67b-2234-5678-90bc-def012345678",
      "status": "READY",
      "total_documents": 14,
      "total_raw_bytes": 4829104,
      "content_hash": "a4b5c6d7e8f90123456789abcdef0123456789abcdef0123456789abcdef0123"
    }
  }
  ```

---

## 2. Documents API

### Upload Document
Uploads a business document binary to secure storage, enforces validation checks, and dispatches bounded text parsing.
- **Method:** `POST`
- **Path:** `/api/v1/workspaces/{workspace_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload`
- **Content-Type:** `multipart/form-data`
- **Permission Required:** `workspace.documents.upload`
- **Form Fields:**
  - `file`: Binary file upload (max 25 MB). Supported: PDF, DOCX, XLSX, CSV, TXT, JSON, JSONL, PNG, JPG, WebP.
- **Response (201 Created):**
  ```json
  {
    "document": {
      "id": "d1e2f3a4-b5c6-7d8e-9f0a-1b2c3d4e5f6a",
      "dataset_version_id": "f5c3e67b-2234-5678-90bc-def012345678",
      "workspace_id": "c9a29e4b-09e4-4c6e-8ff4-93452077e682",
      "name": "leave_policy.pdf",
      "file_type": "PDF",
      "mime_type": "application/pdf",
      "raw_file_size_bytes": 1048576,
      "raw_sha256": "3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c",
      "extracted_text_sample": "Employees receive 25 working days of annual leave per calendar year...",
      "char_count": 4820,
      "word_count": 780,
      "page_count": 3,
      "extraction_status": "COMPLETED",
      "extraction_error": null
    },
    "job": {
      "id": "j1k2l3m4-n5o6-7p8q-9r0s-1t2u3v4w5x6y",
      "status": "COMPLETED",
      "progress_pct": 100
    }
  }
  ```
- **Error Codes:**
  - `400 Bad Request`: Magic byte mismatch, unsupported format, or decompression bomb detected.
  - `409 Conflict`: Identical file content (SHA-256 collision) already exists in this version.
  - `413 Payload Too Large`: File exceeds 25 MB ceiling.

---

### Get Document Detail & Text Preview
Retrieves complete extracted text for display in the Document Preview drawer.
- **Method:** `GET`
- **Path:** `/api/v1/workspaces/{workspace_id}/documents/{document_id}`
- **Permission Required:** `workspace.documents.read`
- **Response (200 OK):**
  ```json
  {
    "document": {
      "id": "d1e2f3a4-b5c6-7d8e-9f0a-1b2c3d4e5f6a",
      "name": "leave_policy.pdf",
      "extracted_text": "Full extracted textual content from all 3 pages..."
    }
  }
  ```

---

### Delete Document
Permanently deletes raw binary from storage, cleans up extracted text, and adjusts dataset version counts.
- **Method:** `DELETE`
- **Path:** `/api/v1/workspaces/{workspace_id}/documents/{document_id}`
- **Permission Required:** `workspace.documents.delete`
- **Response (200 OK):**
  ```json
  {
    "status": "deleted",
    "id": "d1e2f3a4-b5c6-7d8e-9f0a-1b2c3d4e5f6a"
  }
  ```
