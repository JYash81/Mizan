# MIZAN — RENDER FREE STORAGE DURABILITY & PERSISTENCE ASSESSMENT

**Document Version:** 1.0.0  
**Date:** 2026-11-10  
**Classification:** Operational Security & Architecture Audit  
**Target Environment:** Render.com Free Web Service (`https://mizan-api-mq0i.onrender.com`)  

---

## 1. Executive Summary

An architectural audit of Mizan's cloud deployment on the Render Free tier was conducted to establish data durability, state persistence across container restarts, and readiness for enterprise customer workloads.

### Finding
While the core control plane metadata is persisted in an external Hostinger MySQL database, the application server's local file storage (`./storage/`) is strictly **ephemeral**. Any container idle sleep/spin-down, restart, or redeployment completely wipes local files.

### Formal Blocker Statement
> **CRITICAL OPERATIONAL BLOCKER:**  
> Real customer document retention, Gate 1 masked datasets, local vector embeddings, and cryptographic release signature verification are **BLOCKED** from enterprise production SLA on the Render Free tier. The current environment is certified **ONLY** for synthetic testing, prototyping, and demonstration purposes until cloud-native object storage (S3/R2) and an external Key Vault are provisioned.

---

## 2. Storage Tier Classification Matrix

| Component | Physical Path / Target | Storage Class | Persistence Across Restart | Durability Risk | Enterprise Blocker |
|---|---|---|---|---|---|
| **Control Plane DB** | Hostinger MySQL (`srv2209.hstgr.io:3306`) | Managed External RDBMS | **DURABLE** (100% Persisted) | Low (External backup required) | No |
| **Data Plane Documents** | `./storage/data_plane/` | Ephemeral Container Disk | **VOLATILE** (Lost on spin-down) | Critical: Raw & masked files deleted | **YES** |
| **Vector DB (Qdrant)** | `./storage/development/qdrant/` | Local Embedded Index | **VOLATILE** (Lost on restart) | High: Requires re-indexing | **YES** (Degrades Search) |
| **Signing Key Store** | `./storage/keys/` | Ephemeral Container Disk | **VOLATILE** (Fresh key generated) | Critical: Invalids past signatures | **YES** |
| **Audit Trails** | MySQL `audit_events` table | Managed External RDBMS | **DURABLE** (100% Persisted) | Low | No |
| **Runtime Logs** | Container stdout/stderr | Render Log Stream | Transient (24-hour buffer) | Medium | No |

---

## 3. Detailed Component Failure Modes

### 3.1 Data Plane Storage (`./storage/data_plane`)
- **Current Architecture:** Uploaded files and Gate 1 anonymized/masked artifacts are written to `./storage/data_plane/{workspace_id}/{dataset_id}/`.
- **Failure Mode on Render Free:** Render instances spin down after 15 minutes of inactivity. When a new incoming request wakes the container, a fresh ephemeral container filesystem is initialized. Any previously uploaded documents are absent from disk, causing subsequent download or pipeline execution calls to return `404 Not Found` or file I/O errors.
- **Required Remediation:** Migrate `StorageBackend` to S3-compatible cloud storage (Cloudflare R2 or AWS S3) via the existing `STORAGE_BACKEND="s3"` driver configuration.

### 3.2 Cryptographic Key Manager (`./storage/keys`)
- **Current Architecture:** M8/M11/M12 release governance relies on Ed25519 digital signatures to sign Gate 3 releases and staged model artifacts. When the service boots, `KeyManager` checks `./storage/keys/` for `ed25519_signing_key.pem`. If missing, it generates a brand new keypair.
- **Failure Mode on Render Free:** Upon container restart or redeploy, the signing key is regenerated with a new public/private keypair. As a result, releases signed in previous container sessions will fail signature verification checks against the newly generated public key.
- **Required Remediation:** Inject a persistent base64-encoded private key via an environment variable (`MIZAN_SIGNING_KEY_ED25519_PRIVATE`) or integrate with an external KMS (HashiCorp Vault, AWS KMS) so key identity remains immutable across deploys.

### 3.3 Vector Index (`./storage/development/qdrant`)
- **Current Architecture:** RAG pipelines use an embedded Qdrant instance stored locally at `./storage/development/qdrant`.
- **Failure Mode on Render Free:** Container restart erases the vector database files. While source documents in MySQL retain metadata, semantic vector searches fail until the knowledge base is re-embedded.
- **Required Remediation:** Deploy a managed Qdrant Cloud cluster or remote vector service instance.

---

## 4. Remediation Architecture & $0-Cost Strategy

To transition from synthetic verification to enterprise customer readiness under the $0 constraint:

1. **Object Storage ($0 Cloudflare R2):**
   - Cloudflare R2 offers 10 GB/month free storage with zero egress fees.
   - Configure `STORAGE_BACKEND="s3"`, `S3_ENDPOINT_URL="https://<account-id>.r2.cloudflarestorage.com"`, `S3_BUCKET_NAME="mizan-data-plane"`.

2. **Persistent Signing Key ($0 Environment Secret):**
   - Generate a single high-entropy Ed25519 keypair locally using OpenSSL.
   - Store the base64-encoded private key in Render Environment Variables (`SIGNING_KEY_PRIVATE_PEM_B64`).
   - Update `KeyManager` to prioritize the environment variable before falling back to local file generation.

3. **External Vector Database ($0 Qdrant Cloud Free Tier):**
   - Qdrant Cloud provides a 1GB cluster on their free tier.
   - Set `QDRANT_HOST` and `QDRANT_API_KEY` in Render configuration.

---

## 5. Compliance & Certification Conclusion

| Workload Category | Render Free Feasibility | Production Certification Status |
|---|---|---|
| **Synthetic E2E Verification** | Verified Functional | **APPROVED** |
| **API Architecture & RBAC Tests** | Verified Functional | **APPROVED** |
| **Demonstrations & UI Pilots** | Verified Functional | **APPROVED** |
| **Real Customer Data Plane** | Storage Wiped on Spin-down | **BLOCKED** |
| **Long-term Cryptographic Audit** | Key Regenerated on Restart | **BLOCKED** |
