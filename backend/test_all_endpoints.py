"""Comprehensive end-to-end verification script for all Mizan API endpoints and features."""

import os
import sys
import uuid
from typing import Any

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Set test Prometheus scrape token before app initialization
os.environ["PROMETHEUS_SCRAPE_TOKEN"] = "test-scrape-token-e2e-2026"

from fastapi.testclient import TestClient
from app.main import create_app

app = create_app()
client = TestClient(app)

results = []

def run_test(name: str, fn):
    try:
        fn()
        print(f" [PASS] {name}")
        results.append((name, True, None))
    except Exception as e:
        print(f" [FAIL] {name}: {e}")
        results.append((name, False, str(e)))

print("=" * 60)
print("STARTING FULL END-TO-END MIZAN PLATFORM TEST SUITE")
print("=" * 60)

# Global test state
test_id = uuid.uuid4().hex[:8]
test_email = f"e2e_tester_{test_id}@example.com"
test_password = "SecurePassword123!@#"
test_name = f"E2E Tester {test_id}"
session_token = None
csrf_token = None
org_id = None
ws_id = None
dataset_id = None
version_id = None
doc_id = None
suite_id = None
suite_ver_id = None
exp_id = None

# --- 1. SYSTEM & HEALTH ENDPOINTS ---
def test_system_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data.get("data", {}).get("status") == "ok"

def test_system_ready():
    res = client.get("/api/v1/ready")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert res.json().get("data", {}).get("database") == "connected"

def test_system_version():
    res = client.get("/api/v1/version")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

def test_system_info():
    res = client.get("/api/v1/system/info")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

run_test("System: Health Check (/api/v1/health)", test_system_health)
run_test("System: Readiness & DB Connection (/api/v1/ready)", test_system_ready)
run_test("System: Version Info (/api/v1/version)", test_system_version)
run_test("System: System Info (/api/v1/system/info)", test_system_info)

# --- 2. AUTHENTICATION LIFECYCLE ---
def test_auth_registration():
    res = client.post("/api/v1/auth/register", json={
        "full_name": test_name,
        "email": test_email,
        "password": test_password,
        "password_confirm": test_password,
        "terms_accepted": True,
    })
    assert res.status_code == 201, f"Register failed: {res.status_code} {res.text}"
    assert "Registration successful" in res.text

def test_auth_verify_email():
    from app.db.session import SessionLocal
    from app.models.identity import User, AccountStatus
    from datetime import datetime, UTC
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == test_email).first()
        assert user is not None, "Registered user not found in DB"
        user.status = AccountStatus.ACTIVE
        user.email_verified_at = datetime.now(UTC)
        db.commit()

def test_auth_login():
    global session_token, csrf_token
    res = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": test_password,
    })
    assert res.status_code == 200, f"Login failed: {res.status_code} {res.text}"
    data = res.json().get("data", {})
    session_token = data.get("session_token")
    csrf_token = data.get("csrf_token")
    assert session_token, "No session token returned"
    assert csrf_token, "No csrf token returned"

def get_auth_headers():
    return {
        "Authorization": f"Bearer {session_token}",
        "X-CSRF-Token": csrf_token,
    }

def test_auth_me():
    res = client.get("/api/v1/auth/me", headers=get_auth_headers())
    assert res.status_code == 200, f"Get Me failed: {res.status_code} {res.text}"
    data = res.json().get("data", {})
    assert data.get("user", {}).get("email") == test_email

run_test("Auth: Register New User", test_auth_registration)
run_test("Auth: Verify User Email", test_auth_verify_email)
run_test("Auth: Login & Issue Tokens", test_auth_login)
run_test("Auth: Current User Profile (/auth/me)", test_auth_me)

# --- 3. ORGANIZATIONS & WORKSPACES ---
def test_create_organization():
    global org_id
    res = client.post("/api/v1/organizations/", json={
        "name": f"Test Org {test_id}",
        "slug": f"test-org-{test_id}",
    }, headers=get_auth_headers())
    assert res.status_code == 201, f"Create Org failed: {res.status_code} {res.text}"
    org_id = res.json().get("data", {}).get("id")
    assert org_id, "No organization id returned"

def test_get_organization():
    res = client.get(f"/api/v1/organizations/{org_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"Get Org failed: {res.status_code} {res.text}"

def test_create_workspace():
    global ws_id
    res = client.post(f"/api/v1/organizations/{org_id}/workspaces", json={
        "name": f"Test Workspace {test_id}",
        "slug": f"ws-{test_id}",
        "description": "Automated test workspace",
    }, headers=get_auth_headers())
    assert res.status_code == 201, f"Create Workspace failed: {res.status_code} {res.text}"
    ws_id = res.json().get("data", {}).get("id")
    assert ws_id, "No workspace id returned"

def test_list_workspaces():
    res = client.get(f"/api/v1/organizations/{org_id}/workspaces", headers=get_auth_headers())
    assert res.status_code == 200, f"List Workspaces failed: {res.status_code} {res.text}"
    workspaces = res.json().get("data", [])
    assert any(w["id"] == ws_id for w in workspaces)

def test_get_workspace_detail():
    res = client.get(f"/api/v1/workspaces/{ws_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"Get Workspace detail failed: {res.status_code} {res.text}"

run_test("Organizations: Create Organization", test_create_organization)
run_test("Organizations: Get Organization Details", test_get_organization)
run_test("Workspaces: Create Workspace in Org", test_create_workspace)
run_test("Workspaces: List Organization Workspaces", test_list_workspaces)
run_test("Workspaces: Get Workspace Detail", test_get_workspace_detail)

# --- 4. DATASETS & DOCUMENTS ---
def test_create_dataset():
    global dataset_id
    res = client.post(f"/api/v1/workspaces/{ws_id}/datasets", json={
        "name": f"Dataset {test_id}",
        "slug": f"dataset-{test_id}",
        "description": "Test dataset description",
    }, headers=get_auth_headers())
    assert res.status_code == 201, f"Create Dataset failed: {res.status_code} {res.text}"
    dataset_id = res.json().get("dataset", {}).get("id")
    assert dataset_id, "No dataset id returned"

def test_list_datasets():
    res = client.get(f"/api/v1/workspaces/{ws_id}/datasets", headers=get_auth_headers())
    assert res.status_code == 200, f"List Datasets failed: {res.status_code} {res.text}"
    datasets = res.json().get("datasets", [])
    assert any(d["id"] == dataset_id for d in datasets)

def test_get_dataset():
    res = client.get(f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"Get Dataset failed: {res.status_code} {res.text}"

def test_list_dataset_versions():
    global version_id
    res = client.get(f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions", headers=get_auth_headers())
    assert res.status_code == 200, f"List Versions failed: {res.status_code} {res.text}"
    versions = res.json().get("versions", [])
    assert len(versions) > 0, "No initial version created"
    version_id = versions[0]["id"]

def test_upload_document():
    global doc_id
    files = {"file": ("test_doc.txt", b"Mizan Enterprise AI Platform Test Document with content.", "text/plain")}
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
        files=files,
        headers=get_auth_headers(),
    )
    assert res.status_code == 201, f"Upload Document failed: {res.status_code} {res.text}"
    doc_id = res.json().get("document", {}).get("id")
    assert doc_id, "No document id returned"

def test_list_documents():
    res = client.get(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents",
        headers=get_auth_headers(),
    )
    assert res.status_code == 200, f"List Documents failed: {res.status_code} {res.text}"
    docs = res.json().get("documents", [])
    assert any(d["id"] == doc_id for d in docs)

run_test("Datasets: Create Dataset", test_create_dataset)
run_test("Datasets: List Datasets in Workspace", test_list_datasets)
run_test("Datasets: Get Dataset Detail", test_get_dataset)
run_test("Datasets: List Dataset Versions", test_list_dataset_versions)
run_test("Documents: Upload Document to Dataset Version", test_upload_document)
run_test("Documents: List Documents in Version", test_list_documents)

# --- 5. DATA PROTECTION & MASKING ---
def test_list_masking_profiles():
    res = client.get(f"/api/v1/workspaces/{ws_id}/masking-profiles", headers=get_auth_headers())
    assert res.status_code == 200, f"List Masking Profiles failed: {res.status_code} {res.text}"

def test_list_masking_runs():
    res = client.get(f"/api/v1/workspaces/{ws_id}/masking-runs", headers=get_auth_headers())
    assert res.status_code == 200, f"List Masking Runs failed: {res.status_code} {res.text}"

run_test("Data Protection: List Masking Profiles", test_list_masking_profiles)
run_test("Data Protection: List Masking Runs", test_list_masking_runs)

# --- 6. EVALUATION SUITES & VERSIONS ---
def test_create_eval_suite():
    global suite_id
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites",
        json={
            "name": f"Eval Suite {test_id}",
            "description": "Core QA Accuracy Benchmark",
            "source_dataset_id": dataset_id,
            "source_dataset_version_id": version_id,
        },
        headers=get_auth_headers(),
    )
    assert res.status_code in [200, 201], f"Create Suite failed: {res.status_code} {res.text}"
    suite_id = res.json().get("id") or res.json().get("data", {}).get("id")
    assert suite_id, "No evaluation suite id returned"

def test_add_eval_case():
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/cases",
        json={
            "question": "What is Mizan Enterprise Platform?",
            "expected_answer": "Enterprise AI Engineering Platform for sovereign deployment.",
            "split": "DEVELOPMENT",
            "category": "FACTUAL",
            "difficulty": "MEDIUM",
        },
        headers=get_auth_headers(),
    )
    assert res.status_code in [200, 201], f"Add case failed: {res.status_code} {res.text}"

def test_finalize_eval_suite():
    global suite_ver_id
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/finalize",
        json={},
        headers=get_auth_headers(),
    )
    assert res.status_code in [200, 201], f"Finalize suite failed: {res.status_code} {res.text}"
    suite_ver_id = res.json().get("id") or res.json().get("version_id")
    assert suite_ver_id, "No suite version id returned"

def test_list_eval_suites():
    res = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/suites", headers=get_auth_headers())
    assert res.status_code == 200, f"List Evaluation Suites failed: {res.status_code} {res.text}"

def test_get_eval_suite():
    res = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"Get Evaluation Suite failed: {res.status_code} {res.text}"

run_test("Evaluation: Create Evaluation Suite", test_create_eval_suite)
run_test("Evaluation: Add Examination Case", test_add_eval_case)
run_test("Evaluation: Finalize Suite into Immutable Version", test_finalize_eval_suite)
run_test("Evaluation: List Evaluation Suites", test_list_eval_suites)
run_test("Evaluation: Get Evaluation Suite Detail", test_get_eval_suite)

# --- 7. GATE 1 DATASET CLEARANCE FOR EXPERIMENTS ---
def test_gate1_approval_for_experiment():
    from app.db.session import SessionLocal
    from app.models.dataset import DatasetVersion, DatasetVersionStatus
    with SessionLocal() as db:
        ver = db.query(DatasetVersion).filter_by(id=version_id).first()
        if ver:
            ver.status = DatasetVersionStatus.READY
            ver.content_hash = "hash_attested_12345"
            db.commit()

    run_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs",
        json={"dataset_id": dataset_id, "dataset_version_id": version_id},
        headers=get_auth_headers(),
    )
    if run_resp.status_code in [200, 201]:
        m_run_id = run_resp.json().get("id")
        client.post(
            f"/api/v1/workspaces/{ws_id}/masking-runs/{m_run_id}/gate1/approve",
            json={"decision_reason": "Verified and approved for AI testing."},
            headers=get_auth_headers(),
        )

run_test("Approvals: Grant Gate 1 Dataset Clearance", test_gate1_approval_for_experiment)

# --- 8. EXPERIMENTS ENGINE ---
def test_create_experiment():
    global exp_id
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/experiments",
        json={
            "name": f"Experiment {test_id}",
            "description": "Evaluation of model prompt variants",
            "dataset_id": dataset_id,
            "dataset_version_id": version_id,
            "evaluation_suite_id": suite_id,
            "evaluation_suite_version_id": suite_ver_id,
            "baseline_config": {
                "model_identifier": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 256,
            },
        },
        headers=get_auth_headers(),
    )
    assert res.status_code in [200, 201], f"Create Experiment failed: {res.status_code} {res.text}"
    exp_id = res.json().get("id") or res.json().get("data", {}).get("id")
    assert exp_id, "No experiment id returned"

def test_list_experiments():
    res = client.get(f"/api/v1/workspaces/{ws_id}/experiments", headers=get_auth_headers())
    assert res.status_code == 200, f"List Experiments failed: {res.status_code} {res.text}"

def test_get_experiment():
    res = client.get(f"/api/v1/workspaces/{ws_id}/experiments/{exp_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"Get Experiment failed: {res.status_code} {res.text}"

run_test("Experiments: Create Experiment", test_create_experiment)
run_test("Experiments: List Experiments", test_list_experiments)
run_test("Experiments: Get Experiment Detail", test_get_experiment)

# --- 8. APPROVALS GATE 1, 2, 3 ---
def test_gate1_status():
    res = client.get(f"/api/v1/workspaces/{ws_id}/gate1/approvals", headers=get_auth_headers())
    assert res.status_code in [200, 404], f"Gate 1 status check failed: {res.status_code} {res.text}"

def test_gate2_status():
    res = client.get(f"/api/v1/workspaces/{ws_id}/gate2/requests", headers=get_auth_headers())
    assert res.status_code in [200, 404], f"Gate 2 status check failed: {res.status_code} {res.text}"

def test_gate3_status():
    res = client.get(f"/api/v1/workspaces/{ws_id}/gate3/approvals", headers=get_auth_headers())
    assert res.status_code in [200, 404], f"Gate 3 status check failed: {res.status_code} {res.text}"

run_test("Approvals: Gate 1 Privacy Approvals", test_gate1_status)
run_test("Approvals: Gate 2 Proposal Status", test_gate2_status)
run_test("Approvals: Gate 3 Release Approvals", test_gate3_status)

# --- 9. HARDWARE & COST ---
def test_hardware_profiles():
    res = client.get(f"/api/v1/workspaces/{ws_id}/hardware/profiles", headers=get_auth_headers())
    assert res.status_code == 200, f"List Hardware Profiles failed: {res.status_code} {res.text}"

def test_hardware_latest_benchmark():
    res = client.get(f"/api/v1/workspaces/{ws_id}/hardware/benchmarks/latest", headers=get_auth_headers())
    assert res.status_code in [200, 404], f"Hardware benchmark check failed: {res.status_code} {res.text}"

def test_hardware_estimate():
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/hardware/estimate",
        json={
            "model_name": "Llama-3-8B-Instruct",
            "parameter_count_millions": 8000.0,
            "quantization_format": "Q4_K_M",
            "context_length": 2048,
            "batch_size": 1,
        },
        headers=get_auth_headers(),
    )
    assert res.status_code in [200, 201], f"Hardware estimate failed: {res.status_code} {res.text}"

run_test("Hardware: List Hardware Profiles", test_hardware_profiles)
run_test("Hardware: Check Latest Benchmark", test_hardware_latest_benchmark)
run_test("Hardware: Calculate Resource Estimate", test_hardware_estimate)

# --- 10. RECOMMENDATIONS ---
def test_recommendation_profiles():
    res = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/profiles", headers=get_auth_headers())
    assert res.status_code == 200, f"List Recommendation Profiles failed: {res.status_code} {res.text}"

def test_recommendation_runs():
    res = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/runs", headers=get_auth_headers())
    assert res.status_code == 200, f"List Recommendation Runs failed: {res.status_code} {res.text}"

run_test("Recommendations: List Optimization Profiles", test_recommendation_profiles)
run_test("Recommendations: List Recommendation Runs", test_recommendation_runs)

# --- 11. MODEL BUILDING ---
def test_model_building_recipes():
    res = client.get(f"/api/v1/workspaces/{ws_id}/model-building/recipes", headers=get_auth_headers())
    assert res.status_code == 200, f"List Model Recipes failed: {res.status_code} {res.text}"

def test_model_building_runs():
    res = client.get(f"/api/v1/workspaces/{ws_id}/model-building/runs", headers=get_auth_headers())
    assert res.status_code == 200, f"List Model Build Runs failed: {res.status_code} {res.text}"

run_test("Model Building: List Recipes", test_model_building_recipes)
run_test("Model Building: List Build Runs", test_model_building_runs)

# --- 12. ARTIFACT REGISTRY ---
def test_artifact_families():
    res = client.get(f"/api/v1/workspaces/{ws_id}/artifact-registry/families", headers=get_auth_headers())
    assert res.status_code == 200, f"List Artifact Families failed: {res.status_code} {res.text}"

run_test("Artifact Registry: List Model Families", test_artifact_families)

# --- 13. MODEL ZOO & APP ZOO ---
def test_model_zoo():
    res = client.get("/api/v1/zoo/models", headers=get_auth_headers())
    assert res.status_code == 200, f"List Model Zoo failed: {res.status_code} {res.text}"

def test_app_zoo():
    res = client.get("/api/v1/zoo/apps", headers=get_auth_headers())
    assert res.status_code == 200, f"List App Zoo failed: {res.status_code} {res.text}"

run_test("Model Zoo: Browse Model Listings", test_model_zoo)
run_test("App Zoo: Browse App Listings", test_app_zoo)

# --- 14. SITES & RUNTIME ---
def test_customer_sites():
    res = client.get(f"/api/v1/workspaces/{ws_id}/sites", headers=get_auth_headers())
    assert res.status_code == 200, f"List Customer Sites failed: {res.status_code} {res.text}"

def test_customer_runtime_live():
    res = client.get("/api/v1/runtime/live", headers=get_auth_headers())
    assert res.status_code == 200, f"Runtime Live failed: {res.status_code} {res.text}"

def test_customer_runtime_ready():
    res = client.get("/api/v1/runtime/ready", headers=get_auth_headers())
    # 200 when ready or 503 when uninitialized / unassigned model slot
    assert res.status_code in [200, 503], f"Runtime Ready probe failed: {res.status_code} {res.text}"

run_test("Customer Sites: List Edge Sites", test_customer_sites)
run_test("Customer Runtime: Live Health Probe", test_customer_runtime_live)
run_test("Customer Runtime: Readiness Probe", test_customer_runtime_ready)

# --- 15. OPERATIONS CENTRE ---
def test_ops_summary():
    res = client.get(f"/api/v1/ops/metrics/summary?workspace_id={ws_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"Ops Summary failed: {res.status_code} {res.text}"

def test_ops_alerts():
    res = client.get(f"/api/v1/ops/alerts/instances?workspace_id={ws_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"List Ops Alerts failed: {res.status_code} {res.text}"

def test_ops_incidents():
    res = client.get(f"/api/v1/ops/incidents?workspace_id={ws_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"List Incidents failed: {res.status_code} {res.text}"

def test_ops_slos():
    res = client.get(f"/api/v1/ops/slos?workspace_id={ws_id}", headers=get_auth_headers())
    assert res.status_code == 200, f"List SLOs failed: {res.status_code} {res.text}"

def test_ops_prometheus():
    res = client.get(
        "/api/v1/ops/metrics/prometheus",
        headers={"Authorization": "Bearer test-scrape-token-e2e-2026"},
    )
    assert res.status_code == 200, f"Prometheus Scrape failed: {res.status_code} {res.text}"

run_test("Operations: Fleet & Metrics Summary", test_ops_summary)
run_test("Operations: List Alert Instances", test_ops_alerts)
run_test("Operations: List Incidents", test_ops_incidents)
run_test("Operations: List Service Level Objectives", test_ops_slos)
run_test("Operations: Prometheus Scrape Metric Endpoint", test_ops_prometheus)

# --- SUMMARY ---
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print("=" * 60)
print(f"VERIFICATION SUMMARY: {passed}/{total} TESTS PASSED")
print("=" * 60)
if passed < total:
    print("FAILED TESTS:")
    for name, ok, err in results:
        if not ok:
            print(f" - {name}: {err}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED PERFECTLY!")
    sys.exit(0)
