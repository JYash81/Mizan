# Milestone 13 — Customer Runtime Architecture

## 1. Architectural Mission

The Mizan Customer Runtime enables enterprise customers to securely install, verify, and run approved Mizan AI packages entirely on their own infrastructure—whether on-premises servers, air-gapped data centers, or edge compute nodes.

### Key Architectural Invariants:
1. **Customer Data Boundary**: All user prompts, uploaded corporate documents, embeddings, and vector databases reside strictly on customer premises. Zero document content or prompts are ever sent back to the central Mizan control plane.
2. **Offline-Capable Execution**: The Customer Runtime operates completely independently. If the central control plane is unreachable, offline, or disconnected, local inferencing and RAG continue without interruption.
3. **Control Plane / Data Plane Separation**:
   - **Data Plane (Customer Runtime)**: Handles inference (`/v1/chat/completions`), local RAG (`/v1/rag/query`), model weight management, and health probes (`/live`, `/ready`, `/health`).
   - **Management Plane (Site Agent)**: Handles outbound polling, cryptographic package verification, and Blue/Green slot staging commands.

---

## 2. Component Architecture

```
+-------------------------------------------------------------------------------+
|                       CUSTOMER PREMISES (ON-PREM / EDGE)                      |
|                                                                               |
|  +---------------------------+              +------------------------------+  |
|  |     Site Agent Daemon     |              |       Customer Runtime       |  |
|  | (Outbound Polling Only)   |              |  (Local Inferencing & RAG)   |  |
|  |                           |              |                              |  |
|  | * Enrolls Site Identity   |  Stages /    | * /live Probe (Liveness)     |  |
|  | * Polls Signed Commands   |  Unloads     | * /ready Probe (Readiness)   |  |
|  | * Verifies Gate 3 Manifest| -----------> | * /health (Diagnostics)      |  |
|  | * Zero Inbound Ports      |              | * /v1/chat/completions       |  |
|  | * Zero Shell Execution    |              | * /v1/rag/query              |  |
|  +---------------------------+              +------------------------------+  |
|                |                                            ^                 |
|                | Outbound Polling Only                      | Local Traffic   |
|                v                                            | (Port 8080)     |
|  +------------------------------------------+    +-------------------------+  |
|  |   Shared Storage Volumes                 |    |  Customer Users & Apps  |  |
|  |   * mizan-model-storage (Weights/GGUF)   |    +-------------------------+  |
|  |   * mizan-runtime-data (SQLite / Vectors)|                                 |
|  +------------------------------------------+                                 |
+-------------------------------------------------------------------------------+
                         |
                         | Outbound HTTPS / Poll
                         v
+-------------------------------------------------------------------------------+
|                             MIZAN CONTROL PLANE                               |
|                                                                               |
|  * Sites Registry & High-Entropy Tokens     * Signed Command Queue            |
|  * Model Zoo & App Zoo Catalogs             * Ed25519 Attestation Keyring     |
+-------------------------------------------------------------------------------+
```

---

## 3. Local Health and Diagnostic Probes

The Customer Runtime provides three distinct probe endpoints adhering to Kubernetes / container orchestration best practices:

1. **`/api/v1/runtime/live` (Liveness Probe)**:
   - Verifies the Python / Uvicorn process is running and the async event loop is responsive.
   - Returns HTTP 200 `{"status": "alive", "timestamp": "..."}`.
   - Used by container engines to trigger restarts if deadlocked.

2. **`/api/v1/runtime/ready` (Readiness Probe)**:
   - Verifies that the active Blue/Green slot has loaded model weights and successfully passed all mandatory Golden Acceptance Tests.
   - Returns HTTP 200 with `status="ready"` when serving traffic.
   - Returns HTTP 503 Service Unavailable when uninitialized, loading weights, or unhealthy.

3. **`/api/v1/runtime/health` (Diagnostics)**:
   - Returns diagnostic telemetry: process uptime, memory allocated, active slot designation (`SLOT_A` vs `SLOT_B`), engine adapter key, and offline mode confirmation (`offline_mode: true`).

---

## 4. Local Inference and RAG Engine

### OpenAI-Compatible Chat Completions
- Route: `POST /api/v1/runtime/v1/chat/completions`
- Accepts standard OpenAI message format (`system`, `user`, `assistant`).
- Enforces strict offline safety guardrails: detects adversarial prompt injections (e.g. "bypass safety filters") and returns a safe refusal response rather than executing unsafe instructions.
- Returns `offline_executed: true`.

### Local Grounded RAG Queries
- Route: `POST /api/v1/runtime/v1/rag/query`
- Queries local SQLite knowledge tables and vector indexes.
- Returns synthesized answers with grounded citations (`document_id`, `chunk_id`, `snippet`, `score`).
- Strictly operates locally with zero external network connectivity.
