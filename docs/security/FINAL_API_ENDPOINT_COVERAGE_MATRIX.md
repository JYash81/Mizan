# Final API Endpoint Coverage Matrix & Verification Analysis

- **Application Surface:** FastAPI v1 Router (`backend/app/api/v1/router.py`)
- **Total Registered Endpoints:** 239 endpoints across 23 sub-routers
- **E2E Integration Pipeline Coverage:** 51 core scenarios
- **Overall Coverage Status:** **`PARTIAL`** (Core critical-path verified; auxiliary sub-routes covered by modular unit suites)

---

## 1. Architectural Distinction Between Governance Gates

| Governance Gate | Milestone | Purpose & Scope | Cryptographic / Workflow Invariant | API Route Prefix |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 1 Approval** | **M5 / M6** | **Dataset Privacy & PII Masking Clearance** | Mandatory human sign-off on PII masking run before any experiment or model training can reference the dataset version. | `/workspaces/{ws_id}/masking-runs/{run_id}/gate1/approve` |
| **Gate 2 Approval** | **M8** | **Hardware & Cost Proposal Financial Authorization** | Preflight resource estimation and financial clearance proposal approval before launching high-compute training or heavy benchmarks. | `/workspaces/{ws_id}/gate2/requests` |
| **Gate 3 Approval** | **M12** | **Production Release & Deployment Clearance** | Dual-key authorization and release verification before promoting an artifact from Staged to Production / Runtime deployment. | `/workspaces/{ws_id}/gate3/approvals` |

### Investigation of E2E Scenario "Gate 2 Evaluation Approvals"
- **Finding:** In the 51-scenario runner (`backend/test_all_endpoints.py`), test #32 was mislabeled as `"Approvals: Gate 2 Evaluation Approvals"`.
- **Root Cause Analysis:** The test function `test_gate2_status` queries `GET /api/v1/workspaces/{ws_id}/gate2/requests`. In Mizan's architecture, Gate 2 is **Financial and Hardware Proposal Approval**, not "Evaluation Approval". (Evaluation is Milestone 6, whereas Gate 2 is Milestone 8).
- **Semantics Verification:** The full M8 Gate 2 semantics (proposal digests, financial limits, auto-rejection, tamper detection, multi-actor approval) are comprehensively tested in `backend/tests/test_hardware_and_gate2.py` (15/15 passing tests), while the 51-runner tests the endpoint accessibility and auth enforcement.

---

## 2. API Endpoint Coverage Matrix (Sample of Key Endpoints)

| HTTP Method | Route | Authentication | Authorization Scope | E2E Scenario Name | Test Status |
| :--- | :--- | :---: | :--- | :--- | :---: |
| `GET` | `/api/v1/health` | None | Public | System: Health Check | **PASSED** |
| `GET` | `/api/v1/ready` | None | Public | System: Readiness & DB Connection | **PASSED** |
| `GET` | `/api/v1/version` | None | Public | System: Version Info | **PASSED** |
| `GET` | `/api/v1/system/info` | None | Public | System: System Info | **PASSED** |
| `POST` | `/api/v1/auth/register` | None | Public | Auth: Register New User | **PASSED** |
| `POST` | `/api/v1/auth/verify-email` | None | Public | Auth: Verify User Email | **PASSED** |
| `POST` | `/api/v1/auth/login` | None | Public | Auth: Login & Issue Tokens | **PASSED** |
| `GET` | `/api/v1/auth/me` | Session Token | Active User | Auth: Current User Profile | **PASSED** |
| `POST` | `/api/v1/organizations/` | Session Token | Authenticated User | Organizations: Create Organization | **PASSED** |
| `GET` | `/api/v1/organizations/{id}` | Session Token | Org Member | Organizations: Get Organization Details | **PASSED** |
| `POST` | `/api/v1/organizations/{id}/workspaces` | Session Token | Org Admin / Owner | Workspaces: Create Workspace | **PASSED** |
| `GET` | `/api/v1/organizations/{id}/workspaces` | Session Token | Org Member | Workspaces: List Workspaces | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}` | Session Token | Workspace Member | Workspaces: Get Workspace Detail | **PASSED** |
| `POST` | `/api/v1/workspaces/{id}/datasets` | Session Token | Dataset Write | Datasets: Create Dataset | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/datasets` | Session Token | Workspace Read | Datasets: List Datasets | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/datasets/{id}` | Session Token | Workspace Read | Datasets: Get Dataset Detail | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/datasets/{id}/versions` | Session Token | Workspace Read | Datasets: List Versions | **PASSED** |
| `POST` | `/api/v1/workspaces/{id}/datasets/{id}/versions/{ver_id}/documents/upload` | Session Token | Document Write | Documents: Upload Document | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/datasets/{id}/versions/{ver_id}/documents` | Session Token | Workspace Read | Documents: List Documents | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/masking-profiles` | Session Token | Workspace Read | Data Protection: List Profiles | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/masking-runs` | Session Token | Workspace Read | Data Protection: List Runs | **PASSED** |
| `POST` | `/api/v1/workspaces/{id}/evaluation/suites` | Session Token | Eval Write | Evaluation: Create Suite | **PASSED** |
| `POST` | `/api/v1/workspaces/{id}/evaluation/suites/{id}/cases` | Session Token | Eval Write | Evaluation: Add Case | **PASSED** |
| `POST` | `/api/v1/workspaces/{id}/evaluation/suites/{id}/finalize` | Session Token | Eval Write | Evaluation: Finalize Suite | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/evaluation/suites` | Session Token | Workspace Read | Evaluation: List Suites | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/evaluation/suites/{id}` | Session Token | Workspace Read | Evaluation: Get Suite Detail | **PASSED** |
| `POST` | `/api/v1/workspaces/{id}/masking-runs/{id}/gate1/approve` | Session Token | Gate 1 Approver | Approvals: Grant Gate 1 Clearance | **PASSED** |
| `POST` | `/api/v1/workspaces/{id}/experiments` | Session Token | Experiment Write | Experiments: Create Experiment | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/experiments` | Session Token | Workspace Read | Experiments: List Experiments | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/experiments/{id}` | Session Token | Workspace Read | Experiments: Get Experiment Detail | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/gate1/approvals` | Session Token | Workspace Read | Approvals: Gate 1 Privacy Approvals | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/gate2/requests` | Session Token | Workspace Read | Approvals: Gate 2 Proposal Status | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/gate3/approvals` | Session Token | Workspace Read | Approvals: Gate 3 Release Approvals | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/hardware/profiles` | Session Token | Workspace Read | Hardware: List Profiles | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/hardware/benchmarks/latest` | Session Token | Workspace Read | Hardware: Check Benchmark | **PASSED** |
| `POST` | `/api/v1/workspaces/{id}/hardware/estimate` | Session Token | Workspace Read | Hardware: Calculate Estimate | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/recommendations/profiles` | Session Token | Workspace Read | Recommendations: List Profiles | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/recommendations/runs` | Session Token | Workspace Read | Recommendations: List Runs | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/model-building/recipes` | Session Token | Workspace Read | Model Building: List Recipes | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/model-building/runs` | Session Token | Workspace Read | Model Building: List Runs | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/artifact-registry/families` | Session Token | Workspace Read | Artifact Registry: List Families | **PASSED** |
| `GET` | `/api/v1/zoo/models` | Session Token | Workspace Read | Model Zoo: Browse Models | **PASSED** |
| `GET` | `/api/v1/zoo/apps` | Session Token | Workspace Read | App Zoo: Browse Apps | **PASSED** |
| `GET` | `/api/v1/workspaces/{id}/sites` | Session Token | Workspace Read | Customer Sites: List Sites | **PASSED** |
| `GET` | `/api/v1/runtime/live` | None | Public | Customer Runtime: Live Probe | **PASSED** |
| `GET` | `/api/v1/runtime/ready` | None | Public | Customer Runtime: Readiness Probe | **PASSED** |
| `GET` | `/api/v1/ops/metrics/summary` | Session Token | Ops Admin | Operations: Metrics Summary | **PASSED** |
| `GET` | `/api/v1/ops/alerts/instances` | Session Token | Ops Admin | Operations: List Alert Instances | **PASSED** |
| `GET` | `/api/v1/ops/incidents` | Session Token | Ops Admin | Operations: List Incidents | **PASSED** |
| `GET` | `/api/v1/ops/slos` | Session Token | Ops Admin | Operations: List SLOs | **PASSED** |
| `GET` | `/api/v1/ops/metrics/prometheus` | None | Ops Scrape | Operations: Prometheus Scrape | **PASSED** |

---

## 3. Untested Sub-Endpoints in the 51-Scenario Pipeline

While the 51 integration tests cover all critical functional pathways, the following granular sub-endpoints are tested in dedicated test suites (`backend/tests/`) rather than the top-level 51-scenario smoke runner:
- `POST /api/v1/auth/forgot-password` & `POST /api/v1/auth/reset-password` (Verified in `test_auth_api.py`)
- `POST /api/v1/auth/resend-verification` (Verified in `test_auth_api.py`)
- `POST /api/v1/auth/rotate-session` & `DELETE /api/v1/auth/sessions/{id}` (Verified in `test_session_service.py`)
- `POST /api/v1/organizations/{id}/invitations` & `POST /api/v1/invitations/accept` (Verified in `test_invitations_api.py`)
- `POST /workspaces/{ws_id}/gate2/requests/{id}/approve` & `revoke` (Verified in `test_hardware_and_gate2.py`)
- `POST /workspaces/{ws_id}/gate3/approvals/{id}/revoke` (Verified in `test_artifact_registry_and_gate3.py`)
- `POST /workspaces/{ws_id}/ops/rollback/trigger` (Verified in `test_observability_and_rollback.py`)
- `POST /workspaces/{ws_id}/rag/query` & `index` (Verified in `test_rag_pipeline_and_api.py`)
- UAE PII recognizer endpoints and custom regex masks (Verified in `test_uae_recognizers.py`)
