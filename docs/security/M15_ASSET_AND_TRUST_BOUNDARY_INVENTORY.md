# M15 — Asset and Trust Boundary Inventory

**Audit Date:** 2026-11-09  
**Auditor Role:** Principal Application Security Architect  
**Scope:** Complete Mizan Platform (Milestones 1–14)  

---

## 1. Asset Classification Inventory

Mizan processes multiple categories of enterprise assets requiring distinct confidentiality, integrity, and availability controls:

| Asset ID | Asset Name | Description | Confidentiality Tier | Integrity Tier | Storage Location |
|---|---|---|---|---|---|
| **AST-01** | User Credentials | Argon2id password hashes, salt, parameters | Critical | Critical | `users` table |
| **AST-02** | Session & Auth Tokens | 256-bit opaque session cookies, CSRF digests, single-use tokens | Critical | High | `auth_sessions`, `auth_tokens` tables |
| **AST-03** | Platform Ed25519 Signing Keys | Private keys for Gate 1, Gate 2, Gate 3, and Site Agent command signatures | Critical | Critical | `./storage/keys/` (Protected filesystem) |
| **AST-04** | Site Agent Ed25519 Keys | Site-specific private/public keypairs | Critical | Critical | On-premise agent filesystem |
| **AST-05** | Raw Sovereign Customer Documents | Unmasked enterprise documents (PDF, DOCX, XLSX, etc.) | High | High | `storage_data_plane/raw_documents` |
| **AST-06** | Masked Datasets & Text | Gate 1 approved PII-scrubbed datasets | Medium | High | `storage_data_plane/masked_documents` |
| **AST-07** | Vector Store & Embeddings | 384-dimensional FastEmbed dense vectors | High | High | Qdrant local collection directory |
| **AST-08** | Evaluation Exam Questions | Ground-truth questions and scoring rubrics | High | High | `evaluation_cases`, `evaluation_rubrics` tables |
| **AST-09** | Model Weights & Checkpoints | Safetensors, GGUF, AWQ model artifacts | High | Critical | `storage_data_plane/model_artifacts` |
| **AST-10** | Release Manifests & Approvals | Canonical RFC 8785 JSON digests & Ed25519 signatures | Medium | Critical | `artifact_registry`, `gate3_approvals` tables |
| **AST-11** | Customer Runtime Blue/Green Slots | Slot configurations, active model version, golden test results | High | Critical | `runtime_slots`, `runtime_applications` tables |
| **AST-12** | Telemetry & Operational Events | Append-only event journal, Prometheus metrics, incident logs | Low | High | `operational_events`, in-memory Prometheus exporter |

---

## 2. Trust Boundaries Architecture

The following diagram illustrates the primary architectural trust boundaries across the Mizan enterprise platform:

```mermaid
flowchart TB
    subgraph TB01["Untrusted Ingress Zone"]
        UserBrowser["Enterprise User Browser"]
        Attacker["Potential Adversary"]
    end

    subgraph TB02["Mizan Control Plane (FastAPI + SQLAlchemy)"]
        direction TB
        ReverseProxy["Ingress Reverse Proxy (TLS / Security Headers)"]
        APIAuth["Auth & Session Filter (HttpOnly, SameSite, CSRF)"]
        RBAC["RBAC & Tenant Isolation Engine"]
        APIRouters["M1-M14 REST Endpoints"]
        
        subgraph Governance["Cryptographic Governance Engine"]
            Gate1["Gate 1 Attestation Engine"]
            Gate2["Gate 2 Attestation Engine"]
            Gate3["Gate 3 Release Attestation Engine"]
            KeyStore["Platform Ed25519 Key Store"]
        end
    end

    subgraph TB03["Persistent Data Tier"]
        DB[(Relational DB: SQLite / MySQL)]
        Qdrant[(Qdrant Vector Database)]
        LocalStorage[(Encrypted Local Storage / S3)]
    end

    subgraph TB04["External Processing Boundary"]
        Colab["Google Colab / External GPU (Masked Data Only)"]
    end

    subgraph TB05["Customer On-Premise Runtime Tier"]
        direction TB
        SiteAgent["Site Agent (Outbound-Only Poller)"]
        RuntimeEngine["Customer Runtime Engine (Offline Inference)"]
        SlotA["Slot A (Active / Staged)"]
        SlotB["Slot B (Active / Staged)"]
        CustomerPrompts["Customer Prompts (Air-gapped / Local Only)"]
    end

    subgraph TB06["Egress Notification Boundary"]
        LocalStore["Local DB Store (Default)"]
        Webhooks["Operator Webhook Endpoints (SSRF-Hardened)"]
    end

    UserBrowser -->|HTTPS + Session Cookie| ReverseProxy
    Attacker -.->|Untrusted Requests| ReverseProxy
    ReverseProxy --> APIAuth
    APIAuth --> RBAC
    RBAC --> APIRouters
    APIRouters --> Governance
    Governance --> KeyStore
    APIRouters --> DB
    APIRouters --> Qdrant
    APIRouters --> LocalStorage
    
    APIRouters -->|Time-Bounded Signed Export| Colab
    SiteAgent -->|Outbound HTTPS Polling Only (Port 443)| APIRouters
    SiteAgent --> RuntimeEngine
    RuntimeEngine --> SlotA
    RuntimeEngine --> SlotB
    CustomerPrompts --> RuntimeEngine
    
    APIRouters --> TB06
```

---

## 3. Trust Boundary Descriptions & Enforced Controls

### TB-1: Public Ingress $\to$ Control Plane
- **Threats:** Credential stuffing, session hijacking, CSRF, clickjacking, path traversal, injection.
- **Controls:** Strict CORS origins, HttpOnly + SameSite cookies, CSRF double-submit token verification, Argon2id hashing, payload size limit (25 MB), magic byte validation.

### TB-2: Tenant A $\to$ Tenant B (Tenant Boundary)
- **Threats:** Cross-tenant resource enumeration, broken object-level authorization (BOLA), horizontal privilege escalation.
- **Controls:** Mandatory server-side `organization_id` and `workspace_id` filtering on all queries; 404 anti-enumeration responses for unauthorized resource identifiers.

### TB-3: Sovereign Data Plane $\to$ External Processing (Gate 1 Boundary)
- **Threats:** Leakage of unmasked customer PII to cloud training environments or third-party LLMs.
- **Controls:** Hard block: raw datasets cannot be exported. Only Gate 1 approved masked datasets with verified cryptographic attestation can be authorized for external processing via time-bounded `ExternalProcessingAuthorization`.

### TB-4: Control Plane $\to$ Customer Site Agent (Edge Boundary)
- **Threats:** Malicious command injection, replay attacks, man-in-the-middle tampering, rogue agent enrollment.
- **Controls:** Outbound-only polling (agent exposes zero listening ports); Ed25519 command signing; single-use nonces; allowlisted typed commands only (zero arbitrary shell execution).

### TB-5: Customer Inference $\to$ Control Plane (Telemetry Boundary)
- **Threats:** Exposure of confidential prompts or proprietary queries via monitoring pipelines.
- **Controls:** Zero prompts or completions transmitted in telemetry. Telemetry filtering purges sensitive keys and masks tokens before metric aggregation. Explicit opt-in `sync_consent`.

### TB-6: Control Plane $\to$ External Webhooks (Egress Boundary)
- **Threats:** Server-Side Request Forgery (SSRF) targeting internal networks, localhost, or cloud metadata endpoints (`169.254.169.254`).
- **Controls:** Comprehensive IP filter blocking RFC 1918, loopback, link-local, multicast, and metadata addresses; zero redirects allowed; pre-socket DNS resolution validation.
