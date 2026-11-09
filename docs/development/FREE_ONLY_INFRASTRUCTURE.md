# Mizan Free-Only Infrastructure & Cost Policy Specification

**Authoritative Mandate:** Mandatory Architecture Decision Override for Milestone 5 and All Remaining MVP Development  
**Effective Date:** 2026-11-08  
**Additional Budget:** $0.00 (Zero)  
**Host Target:** Windows 10, Intel Core i5, 8 GB RAM, No Dedicated GPU  
**Status:** ACTIVE & ENFORCED  

---

## 1. Non-Negotiable Cost Policy

Mizan is architected to operate with **ZERO additional expenditure** during development, testing, evaluation, and MVP phases. Under no circumstances may any component, automated workflow, or developer tool incur financial charges, initiate subscriptions, or trigger billable compute.

### Application-Level Cost Configuration
The backend application runtime strictly enforces the following immutable flags:

```ini
# Core Free-Only Cost Policy
ALLOW_PAID_PROVIDERS=false
ALLOW_BILLABLE_EXTERNAL_COMPUTE=false
ALLOW_PAID_STORAGE=false
ALLOW_PAID_EMBEDDING_APIS=false
ALLOW_AUTOMATIC_BILLING=false
```

### Mandatory Cost Invariants
1. **Default Rejection:** Any provider, model tier, storage backend, or database requiring payment is rejected at initialization time.
2. **Hard Rate-Limit Stop:** If a free external quota (e.g. Gemini free-tier) is exhausted, the application immediately stops and returns an explicit `HTTP 429 Quota Exceeded` error. It **NEVER** silently falls back to a paid tier or enables pay-as-you-go billing.
3. **No Automatic Account Upgrades:** The platform never requests, stores, or supplies credit cards or payment credentials.
4. **Offline First:** All core capabilities (masking, embeddings, vector search, RAG evaluation, mock generation) function 100% offline without internet access.

---

## 2. Infrastructure Inventory & Dependency Classification

To maintain rigorous governance, all dependencies are categorized into **Free Software (Local/Self-Hosted)** versus **Free Hosted Services (Cloud/Remote)**.

### A. Free Software (Local, Zero External Calls, Zero Quotas)

| Component | Technology | License | Account Required | Network Required | Hardware Footprint |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Framework** | FastAPI / Python 3.12 | MIT | No | No | ~60 MB RAM |
| **Relational Database** | SQLite (Dev/Test) | Public Domain | No | No | ~10 MB RAM |
| **Vector Database** | Qdrant Local Disk Mode (`qdrant-client`) | Apache 2.0 | No | No | ~50 MB RAM |
| **Embedding Engine** | FastEmbed (`fastembed` + ONNX Runtime) | Apache 2.0 | No | No (after cached) | ~150 MB RAM (CPU only) |
| **PII Detection** | Presidio Analyzer (`presidio-analyzer`) | MIT | No | No | ~80 MB RAM |
| **Data Plane Storage** | `LocalStorageProvider` (`storage/data_plane/`) | Proprietary (Mizan) | No | No | Disk space only |
| **Frontend Framework** | React 18 + Vite + Tailwind CSS | MIT | No | No | Browser memory |
| **Mock LLM Provider** | Pure Python Mock Generator | Proprietary (Mizan) | No | No | < 1 MB RAM |

### B. Free Hosted Services (Subject to Quotas & Privacy Constraints)

| Service | Intended Role | Cost / Tier | Free Quota Constraints | Privacy & Data Boundary |
| :--- | :--- | :--- | :--- | :--- |
| **Google Gemini Free Tier** | Non-confidential dev experiments, synthetic benchmark exams | $0 (Free Tier with AI Studio key) | 15 RPM / 1M TPM / 1,500 RPD (gemini-1.5-flash) | **STRICT PROHIBITION:** Must NEVER receive confidential business documents or raw data. Opt-in only. |
| **Ollama (Local)** | Local LLM execution (e.g. Qwen2.5-0.5B, Llama3.2-1B) | $0 (Open Source) | Limited by host 8 GB RAM and CPU | 100% Sovereign (runs locally on PC). |
| **Hostinger Business Plan** | Remote MySQL staging & deployment | Existing Subscription ($0 additional) | Hostinger plan limits | Isolated credentials. No dev test drops production tables. |
| **Google Colab (Free)** | Manual, user-driven GPU notebook experiments | $0 (Free Compute Tier) | Preemptible session; no SLA | Non-critical only; Mizan runtime NEVER depends on Colab. |

---

## 3. Vector Database Architecture: Qdrant Local Mode

Mizan selects **Qdrant** via its official Python client in persistent local mode:

```python
from qdrant_client import QdrantClient

client = QdrantClient(path="storage/development/qdrant")
```

### Architectural Realities & Guarantees
1. **Zero External Daemon:** Operates embedded directly inside the Python process using local disk storage (RocksDB / memory-mapped storage). Does not require Docker or background daemons.
2. **Single-Process Constraint:** Embedded local disk mode acquires a file lock on `storage/development/qdrant`. It is strictly bounded to a single application process during local execution.
3. **Seamless Future Migration:** The `VectorStoreProvider` interface exposes standard operations (`upsert_vectors`, `search_vectors`, `delete_collection`). In production, transitioning to a remote Qdrant cluster requires only changing connection arguments (`url="http://qdrant-server:6333"`), without modifying RAG or business logic.

---

## 4. Local Embedding Generation: FastEmbed

Mizan selects **FastEmbed** for local CPU embedding generation:
- **Default Candidate Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  - Dimensions: 384
  - License: Apache 2.0
  - Runtime: ONNX Runtime (CPU quantized, highly optimized for Intel i5)
  - Multilingual Support: English, Arabic, and 50+ languages.
- **Resource Discipline:**
  - FastEmbed weights (~120 MB) are downloaded only on demand and cached locally in `storage/models/fastembed/`.
  - Application startup never blocks on large automatic downloads.
  - Zero PyTorch installation required (saves ~2 GB disk space and hundreds of MBs of RAM).

---

## 5. Privacy Policy & External Provider Access Guard

In accordance with Mizan High-Level Design and Gate 1 invariants:
1. **Gate 1 Approval is Necessary but Insufficient for Cloud Sharing:** An approved Gate 1 masked dataset is authorized for internal processing, but sending any data to third-party cloud APIs (such as Gemini) requires **explicit customer opt-in** and a **Data Classification Check**.
2. **Provider Guard Pipeline:**
   ```
   [Inference Request]
          │
          ▼
   [Cost Policy Check: Is Provider Free?] ── No ──► [HTTP 402/403 Rejected]
          │ Yes
          ▼
   [Data Classification Check: Is Data Confidential?] ── Yes (External) ──► [Blocked: Require Local/Mock]
          │ No or Masked + Authorized
          ▼
   [Rate Limit / Quota Check] ── Quota Exhausted ──► [HTTP 429 Stop (No Auto-Billing)]
          │ Available
          ▼
   [Execute Inference]
   ```
