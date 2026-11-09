# Mizan Document Ingestion Security Specification

**Authoritative Baseline:** High-Level Design & Master Directive  
**Status:** ACTIVE  
**Updated:** 2026-11-08  

---

## 1. Threat Model & Security Principles

Document upload is one of the highest-risk attack surfaces in multi-tenant SaaS platforms. Mizan enforces a defense-in-depth posture:
1. **Never Trust User Metadata:** File extensions, user-supplied content types, and client-reported file names are treated as untrusted input.
2. **Strict Physical and Logical Isolation:** Uploaded files are partitioned strictly by `workspace_id` in storage and database.
3. **Bounded Processing Limits:** Every parser runs under strict CPU, memory, and timeout constraints to prevent denial-of-service (DoS) attacks.
4. **Data Sovereignty:** Raw uploaded business files remain isolated in the `raw_uploads` bucket and are never passed to external AI services or control plane metadata stores.

---

## 2. Ingestion Defense Controls

### A. File Size Enforcement
- Hard upload ceiling enforced at both reverse proxy/FastAPI layer and file streaming validator: **25 MB** (configurable via `STORAGE_MAX_UPLOAD_SIZE_BYTES`).
- Requests with bodies or files exceeding this limit are terminated with HTTP 413 (Payload Too Large) before loading into memory.

### B. Magic Byte Inspection
Files are inspected for authoritative magic headers:
- **PDF:** Must begin with `%PDF-` (`0x25 0x50 0x44 0x46 0x2D`).
- **DOCX / XLSX (ZIP-based OOXML):** Must begin with PK header `PK\x03\x04` (`0x50 0x4B 0x03 0x04`).
- **PNG:** Must begin with `\x89PNG\r\n\x1a\n` (`0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A`).
- **JPEG:** Must begin with `\xff\xd8\xff` (`0xFF 0xD8 0xFF`).
- **WebP:** Must begin with `RIFF....WEBP`.
- **Text / CSV / JSON:** Verified to be valid UTF-8/ASCII without null bytes (`\x00`) or binary control characters.

Files whose extension does not match their detected magic header are rejected with HTTP 400 (Bad Request).

### C. Decompression Bomb Defenses (DOCX / XLSX / ZIP)
DOCX and XLSX files are zipped XML archives. To prevent "zip bomb" amplification attacks:
- The zip central directory is inspected before extracting.
- **Max Compression Ratio:** The ratio of uncompressed bytes to compressed bytes must not exceed **100:1**.
- **Max Total Uncompressed Size:** The cumulative uncompressed size of all archive members must not exceed **100 MB**.
- **Max File Count:** An archive must not contain more than **1,000 files**.
- Nested archives are rejected.

### D. Path Traversal & Filename Sanitization
- File names are stripped of path separators (`/`, `\`, `..`), null bytes, and non-printable control characters.
- In storage, physical files are named using deterministic UUIDs rather than the user's filename.

### E. Untrusted Parser Sandboxing & Failure Containment
- Document parsers are written in pure Python without calling shell subprocesses.
- Parsing errors (corrupted PDF streams, invalid XML, syntax errors) are trapped safely within the worker and recorded as `FAILED` extraction status in the database with an explanatory message, rather than bubbling up as unhandled server 500s.
