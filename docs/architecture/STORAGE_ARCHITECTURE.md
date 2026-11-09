# Mizan Storage Architecture

**Authoritative Baseline:** High-Level Design (`docs/reference/mizan_hld.png`) & Master Directive  
**Status:** ACTIVE  
**Updated:** 2026-11-08  

---

## 1. Overview and Principles

Mizan enforces strict architectural separation between the **Control Plane (Front Desk)** and the **Data Plane (Workshop)**:
- **Zero Raw Data in Control Plane:** The Control Plane metadata store (relational database) never holds raw uploaded document contents or raw model weights. It only holds references, metadata, hashes, and small preview snippets.
- **Provider Decoupling:** Storage is encapsulated behind an abstract provider interface (`StorageProvider`), allowing local development on private disk and seamless deployment to S3-compatible cloud storage (e.g. AWS S3, Cloudflare R2, MinIO) in staging and production.
- **Partitioned Logical Buckets:** Files are categorized into discrete logical buckets with distinct access policies, encryption requirements, and lifecycle rules.

---

## 2. Logical Storage Buckets

| Bucket Identifier | Purpose | Sensitivity | Permitted Consumers |
| :--- | :--- | :--- | :--- |
| `raw_uploads` | Raw business uploads (PDF, DOCX, CSV, etc.) before masking. | **CRITICAL / PII** | Document extraction service and PII masking engine only. |
| `masked_datasets` | Anonymized / masked datasets approved at **Gate 1**. | **CONTROLLED** | Internal RAG indexer, exam generator, and permitted model trials. |
| `evaluations` | Synthetic evaluation suites, test queries, rubrics ("exams"). | **INTERNAL** | Benchmark runner, experiment orchestrator. |
| `artifacts` | Intermediate model weights, fine-tuning checkpoints, LoRA adapters. | **HIGH** | Build pipeline, quantization scripts. |
| `releases` | Final signed packages, GGUF/AWQ models, release manifests. | **PROTECTED** | Model and App Zoo distributor. |
| `customer_packages`| Downloadable deployment archives for customer runtimes. | **PROTECTED** | Customer site agents over mTLS. |

---

## 3. Storage Provider Interface

```python
class StorageProvider(ABC):
    @abstractmethod
    def put_object(
        self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> StorageObjectMetadata: ...

    @abstractmethod
    def get_object(self, bucket: str, key: str) -> tuple[bytes, StorageObjectMetadata]: ...

    @abstractmethod
    def delete_object(self, bucket: str, key: str) -> bool: ...

    @abstractmethod
    def object_exists(self, bucket: str, key: str) -> bool: ...

    @abstractmethod
    def generate_download_url(self, bucket: str, key: str, expires_in_seconds: int = 3600) -> str: ...
```

### Key Generation and Path Structure
Storage keys follow a strict hierarchical format that enforces tenant isolation at the storage level:
`{workspace_id}/{entity_type}/{entity_id}/{safe_filename_or_hash}`

Example:
`c9a29e4b-09e4-4c6e-8ff4-93452077e682/documents/85e13d9a-1c88-466d-8869-d477bb0b537c/contract.pdf`

---

## 4. Local Storage Provider Security (Development)

In local development, `LocalStorageProvider` writes to `./storage/data_plane/{bucket}/{key}`:
- **Path Traversal Mitigation:** All keys are resolved against the canonical bucket root. If the resolved absolute path does not start with the bucket root path (e.g. attempting `../../etc/passwd`), the operation raises `SecurityViolationError` immediately.
- **Atomic Writes:** New files are written to a temporary file in the target directory and atomically moved into place using `os.replace` to prevent partial writes.
- **Integrity Validation:** SHA-256 digests are computed during the write and returned in the object metadata.
