# Milestone 13 Completion Report — Customer Runtime & Site Agent

## Executive Summary

Milestone 13 (Customer Runtime & Site Agent) has been designed, implemented, tested, and integrated into the Mizan platform.

The Milestone 13 implementation enables enterprise customers to securely receive an approved Mizan application, verify its Gate 3 Ed25519 attestation, install it inside their own private environment (on-premise, customer cloud, or air-gapped edge node), serve local inferencing and RAG completely offline, manage Blue/Green deployment slots (Slot A and Slot B), and gate releases through automated Golden Acceptance Tests.

---

## 1. Verification Evidence Summary

| Verification Category | Status | Evidence / Metrics |
| :--- | :--- | :--- |
| **Backend Full Regression** | **PASSED** | 218 / 218 tests passing (100% success rate across 18 test files) |
| **Focused M13 Backend Suite** | **PASSED** | 7 / 7 comprehensive test suites passing in `tests/test_customer_runtime_and_site_agent.py` |
| **Frontend Test Suite** | **PASSED** | 47 / 47 tests passing (100% success rate across 12 test files) |
| **Backend Code Quality** | **PASSED** | `ruff check app tests` 100% clean (0 errors, 0 warnings) |
| **Frontend Type Safety** | **PASSED** | `npx tsc -b` exited with code 0 (zero errors) |
| **Frontend Code Quality** | **PASSED** | `npm run lint` exited with code 0 (zero errors) |
| **Production Build** | **PASSED** | `npm run build` Vite production build successful (7.51s) |
| **Database Migrations** | **PASSED** | Alembic revision `20261109_0014` verified forward & backward |
| **Additional Spend** | **$0.00** | Zero paid cloud resources, zero paid API inference, zero external fees |
| **Preserved Blocker** | **PRESERVED** | `M2.B1 Step 3 — Remote MySQL Concurrency Verification: BLOCKED` intact |

---

## 2. Key Demonstrations (A through I)

### Demonstration A: Customer Site Registration & High-Entropy Enrollment Tokens
- Implemented `CustomerSite` and `SiteEnrollmentToken` models.
- Administrator registers deployment sites (`site_key`, `site_name`, `description`).
- High-entropy single-use tokens are generated with 256 bits of cryptographically secure random entropy (`secrets.token_urlsafe(32)`).
- SHA-256 digests are stored; raw tokens are never persisted in plaintext.
- Strict expiration windows (default: 60 minutes) and single-use guarantee: attempting to consume a token twice raises `EnrollmentTokenAlreadyConsumedError` (HTTP 410).

### Demonstration B: Site Agent Enrollment & Public Key Fingerprinting
- Site Agent generates an Ed25519 keypair locally; private keys strictly remain on customer premises.
- Control plane validates token digest, marks token consumed, records `SiteAgentIdentity` with public key fingerprint (SHA-256), and transitions site status to `ACTIVE`.
- Agent heartbeats report platform information (CPU, RAM, OS) and retrieve pending command counters.

### Demonstration C: Outbound-Only Polling & Ed25519 Signed Commands
- Outbound polling model: Site Agent initiates all HTTP requests. Strictly zero listening ports are exposed on customer premises.
- Signed commands use dedicated purpose `SITE_AGENT_COMMAND`.
- Every command includes unique `nonce`, `expires_at`, `payload_digest`, and Ed25519 signature.
- Replay prevention: replaying a consumed command is rejected with `ReplayedNonceError` (HTTP 409).
- Expiration prevention: expired commands are rejected with `ExpiredCommandError` (HTTP 410).
- Strict allowlist: only typed commands (`FETCH_APPROVED_PACKAGE`, `VERIFY_PACKAGE`, `STAGE_PACKAGE`, `REPORT_RUNTIME_STATUS`, `REQUEST_GOLDEN_TEST`, `SYNC_APPROVED_METADATA`) are permitted. Zero arbitrary shell execution is ever invoked.

### Demonstration D: Package Verification, Gate 3 Attestation & Hardware Preflight
- Package installation (`verify_and_install_package`) verifies:
  1. M11 `ModelVersion` status is `APPROVED`.
  2. Gate 3 Ed25519 release signature is verified against canonical payload.
  3. App license allows offline/on-premise deployment (rejects restricted licenses).
  4. Hardware preflight check: compares site platform host memory against package minimum RAM. If host RAM is insufficient, installation is blocked with `HardwarePreflightFailedError`.

### Demonstration E: Blue/Green Deployment Slots (Slot A and Slot B)
- Every installed application maintains `SLOT_A` and `SLOT_B`.
- Active slot serves live traffic; candidate slot holds staged releases.
- Unload-and-load staging semantics: prevents OOM crashes on memory-constrained nodes by unloading previous weights before loading candidate tensors.
- Readiness transitions: `UNINITIALIZED` -> `LOADING` -> `READY` (or `UNHEALTHY`).

### Demonstration F: Golden Acceptance Test Runner (8 Categories)
- Versioned acceptance test suite bound to app manifest and model digest.
- Evaluates 8 core categories:
  1. `startup`: runtime process startup and `/live` probe.
  2. `model_loading`: model weights and tensor mapping integrity.
  3. `inference_smoke`: deterministic baseline prompt and completion.
  4. `output_schema`: OpenAI-compatible schema compliance.
  5. `rag_retrieval_citations`: local grounded citations with chunk IDs.
  6. `safety_abstention`: safe refusal/abstention on adversarial inputs.
  7. `offline_path`: zero external network calls during inference.
  8. `resource_limits`: peak memory within slot budget.
- Privacy-safe logging: customer prompt text and corporate data are strictly omitted from execution logs.

### Demonstration G: Golden Test Gating & Atomic Slot Promotion
- Mandatory Golden Test failures block promotion: slot readiness becomes `UNHEALTHY`, and `/slots/activate` fails with HTTP 412 Precondition Failed (`SlotActivationBlockedError`).
- When all mandatory tests pass, authorized operator initiates promotion with human justification.
- Atomic switch: traffic moves to candidate slot; previous slot is retained in `STAGED` state for instant rollback.
- Append-only audit logging: `RuntimeActivationEvent` records previous slot, new slot, actor ID, and switch reason.

### Demonstration H: Manual Slot Rollback
- Operator can trigger immediate rollback to the alternate slot via dashboard or API.
- Rollback event is recorded with `ROLLBACK: <reason>` in audit trail.

### Demonstration I: Customer Runtime Offline Inference & Health Probes
- Distinct container probes:
  - `/api/v1/runtime/live`: process liveness.
  - `/api/v1/runtime/ready`: active slot traffic readiness.
  - `/api/v1/runtime/health`: diagnostic metrics.
- Local OpenAI-compatible chat completions (`/api/v1/runtime/v1/chat/completions`) and local grounded RAG queries (`/api/v1/runtime/v1/rag/query`).
- Safety guardrails: prompts containing adversarial patterns trigger safe refusal.
- Fully offline execution: customer runtime operates uninterrupted when WAN or control plane is disconnected.

---

## 3. Deployment Artifacts

1. **Docker Compose Package (`deploy/docker-compose/`)**:
   - `Dockerfile.runtime`: Non-root (`UID 10001`), hardened multi-stage image.
   - `Dockerfile.agent`: Outbound-only management daemon.
   - `docker-compose.yml`: Multi-container configuration with `mizan-model-storage` and `mizan-runtime-data` persistent volumes.
   - `README.md`: Customer deployment runbook covering air-gapped installation, upgrades, and backups.

2. **Helm Chart (`deploy/helm/mizan-customer-runtime/`)**:
   - `Chart.yaml`, `values.yaml`
   - Hardened non-root Kubernetes manifests: `deployment-runtime.yaml`, `deployment-agent.yaml`, `service.yaml`, `configmap.yaml`, `secret.yaml`, `pvc.yaml`, `serviceaccount.yaml`, `rbac.yaml`.
   - Distinct `startupProbe`, `livenessProbe`, and `readinessProbe`.

3. **Frontend Console (`frontend/src/features/runtime/`)**:
   - `SitesPage`: Workspace customer sites list, enrollment token generation, status monitoring.
   - `RuntimeDashboardPage`: Blue/Green slot cards, golden test breakdown, atomic promotion & rollback controls, and offline inference testing console.
   - Components: `SlotCard.tsx`, `GoldenTestResultsCard.tsx`, `SiteEnrollmentModal.tsx`, `SlotActivationModal.tsx`.

---

## 4. Strict Milestone Boundaries

- **M14 Boundary**: No automated production telemetry collection, no metric-threshold alerting triggers, no automated rollback engines.
- **M15 Boundary**: No penetration testing or ISO/SOC2 certification claims.
- **Cost Policy**: 100% adherence to $0.00 additional spend policy.
- **Preserved Blocker**: `M2.B1 Step 3 — Remote MySQL Concurrency Verification: BLOCKED` preserved unchanged.
