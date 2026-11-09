"""Integration tests for Mizan Milestone 6 Evaluation Engine Services, Workflows, and REST APIs."""

from __future__ import annotations

import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.dataset import DatasetVersion, DatasetVersionStatus
from app.models.identity import AccountStatus, User
from app.modules.auth.services import password_service, session_service
from app.modules.storage import (
    LocalStorageProvider,
    set_storage_provider_override,
)
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def eval_test_env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    def _override_get_db():
        db = Session(engine, expire_on_commit=False)
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db

    tmp_dir = tempfile.TemporaryDirectory()
    storage = LocalStorageProvider(tmp_dir.name)
    set_storage_provider_override(storage)

    client = TestClient(app)
    db = Session(engine, expire_on_commit=False)

    owner = User(
        full_name="Maryam Evaluation Lead",
        email="maryam@mizan.ae",
        normalized_email="maryam@mizan.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add(owner)
    db.commit()

    owner_sess = session_service.create_session(db, owner.id)
    org, _ = organization_service.create_organization(db, owner.id, "Mizan Evaluation Corp", "mizan-eval-corp")
    ws, _ = workspace_service.create_workspace(db, org.id, owner.id, "Evaluation Lab", "eval-lab")

    # Second user / workspace for tenant isolation tests
    other_user = User(
        full_name="Other User",
        email="other@mizan.ae",
        normalized_email="other@mizan.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add(other_user)
    db.commit()
    other_sess = session_service.create_session(db, other_user.id)
    other_org, _ = organization_service.create_organization(db, other_user.id, "Other Org", "other-org")
    other_ws, _ = workspace_service.create_workspace(db, other_org.id, other_user.id, "Other Lab", "other-lab")
    db.commit()

    yield {
        "client": client,
        "engine": engine,
        "owner": owner,
        "org_id": org.id,
        "ws_id": ws.id,
        "other_ws_id": other_ws.id,
        "storage": storage,
        "owner_cookies": {"mizan_session": owner_sess.session_token},
        "owner_headers": {"X-CSRF-Token": owner_sess.csrf_token},
        "other_cookies": {"mizan_session": other_sess.session_token},
        "other_headers": {"X-CSRF-Token": other_sess.csrf_token},
    }

    set_storage_provider_override(None)
    tmp_dir.cleanup()


def test_suite_crud_and_tenant_isolation(eval_test_env):
    """Verify suite creation, listing, retrieval, and strict tenant isolation."""
    client = eval_test_env["client"]
    ws_id = eval_test_env["ws_id"]
    other_ws_id = eval_test_env["other_ws_id"]
    cookies = eval_test_env["owner_cookies"]
    headers = eval_test_env["owner_headers"]
    other_cookies = eval_test_env["other_cookies"]

    # 1. Create suite
    create_payload = {
        "name": "Finance & Banking Exam Suite",
        "description": "Exams for corporate banking policies and credit guidelines.",
        "suite_type": "BENCHMARK",
        "language": "en",
        "tags": ["finance", "banking", "compliance"],
    }
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites",
        json=create_payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 201
    suite_data = res.json()
    suite_id = suite_data["id"]
    assert suite_data["name"] == "Finance & Banking Exam Suite"
    assert suite_data["status"] == "DRAFT"
    assert suite_data["total_cases"] == 0

    # 2. List suites in workspace
    res = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/suites", cookies=cookies)
    assert res.status_code == 200
    suites = res.json()
    assert len(suites) == 1
    assert suites[0]["id"] == suite_id

    # 3. Get suite by ID
    res = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}", cookies=cookies)
    assert res.status_code == 200
    assert res.json()["id"] == suite_id

    # 4. Anti-enumeration: Other workspace trying to access suite gets 404
    res = client.get(f"/api/v1/workspaces/{other_ws_id}/evaluation/suites/{suite_id}", cookies=other_cookies)
    assert res.status_code == 404


def test_gate1_enforcement_for_exam_generation(eval_test_env):
    """INVARIANT: Verify exam generation fails closed with HTTP 403 if Gate 1 approval is absent."""
    client = eval_test_env["client"]
    ws_id = eval_test_env["ws_id"]
    cookies = eval_test_env["owner_cookies"]
    headers = eval_test_env["owner_headers"]

    # 1. Create a suite
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites",
        json={"name": "Gate1 Test Suite"},
        cookies=cookies,
        headers=headers,
    )
    suite_id = res.json()["id"]

    # 2. Create unapproved dataset version via API
    ds_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets",
        json={"name": "Unapproved Dataset", "slug": "unapproved-ds"},
        cookies=cookies,
        headers=headers,
    )
    assert ds_resp.status_code == 201
    unapproved_dv_id = ds_resp.json()["version"]["id"]

    # 3. Attempt exam generation without Gate 1 approval -> MUST fail closed with 403
    gen_payload = {
        "dataset_version_id": unapproved_dv_id,
        "target_count": 5,
        "generator_type": "RULE_BASED",
    }
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/generate-cases",
        json=gen_payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 403
    assert "Gate 1" in str(res.json())


def test_exam_generation_with_gate1_approval_and_offsets(eval_test_env):
    """Verify exam generation succeeds with approved Gate 1 masked dataset and generates categorized cases."""
    client = eval_test_env["client"]
    ws_id = eval_test_env["ws_id"]
    cookies = eval_test_env["owner_cookies"]
    headers = eval_test_env["owner_headers"]

    db = Session(eval_test_env["engine"], expire_on_commit=False)

    # 1. Create suite
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites",
        json={"name": "AML Compliance Suite"},
        cookies=cookies,
        headers=headers,
    )
    suite_id = res.json()["id"]

    # 2. Create dataset and upload document via API
    ds_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets",
        json={"name": "AML Dataset", "slug": "aml-ds"},
        cookies=cookies,
        headers=headers,
    )
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["dataset"]["id"]
    dv_id = ds_resp.json()["version"]["id"]

    sample_text = (
        "Mizan Anti-Money Laundering and Fraud Compliance Directive.\n"
        "Suspicious transactions exceeding 100,000 AED must be reported to the Compliance Department within 24 hours.\n"
        "Customer due diligence and KYC verification must be updated annually for all high-risk accounts.\n"
        "Sanctioned entity screening is performed automatically before any international wire clearance."
    )
    upload_res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{dv_id}/documents/upload",
        files={"file": ("aml_policy.txt", sample_text.encode("utf-8"), "text/plain")},
        cookies=cookies,
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document"]["id"]

    # Finalize version to READY
    ver = db.query(DatasetVersion).filter_by(id=dv_id).first()
    ver.status = DatasetVersionStatus.READY
    ver.content_hash = "aml_policy_hash_123"
    db.commit()

    # 3. Trigger Masking Run
    run_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs",
        json={"dataset_id": dataset_id, "dataset_version_id": dv_id},
        cookies=cookies,
        headers=headers,
    )
    assert run_resp.status_code == 201
    mask_run_id = run_resp.json()["id"]

    # 4. Gate 1 Human Approval via API
    approve_res = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{mask_run_id}/gate1/approve",
        json={"decision_reason": "Approved for evaluation exam generation."},
        cookies=cookies,
        headers=headers,
    )
    assert approve_res.status_code == 201

    # 5. Generate cases via API
    gen_payload = {
        "dataset_version_id": dv_id,
        "target_count": 6,
        "generator_type": "RULE_BASED",
        "include_unanswerable": True,
    }
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/generate-cases",
        json=gen_payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 200
    gen_result = res.json()
    assert gen_result["generated_count"] >= 3

    # 6. Verify cases in suite
    res = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/cases", cookies=cookies)
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) == gen_result["generated_count"]

    # Verify split, categories, and source attribution
    categories = {c["category"] for c in cases}
    splits = {c["split"] for c in cases}
    assert len(categories) > 0
    assert any(s in ("DEVELOPMENT", "VALIDATION", "HOLDOUT") for s in splits)

    answerable_cases = [c for c in cases if not c["is_unanswerable"]]
    assert len(answerable_cases) > 0
    first_ans = answerable_cases[0]
    assert doc_id in first_ans["source_document_ids"]


def test_case_review_and_manual_creation(eval_test_env):
    """Verify human review actions (approve, edit, reject) and manual case creation."""
    client = eval_test_env["client"]
    ws_id = eval_test_env["ws_id"]
    cookies = eval_test_env["owner_cookies"]
    headers = eval_test_env["owner_headers"]

    # 1. Create suite
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites",
        json={"name": "Manual Review Suite"},
        cookies=cookies,
        headers=headers,
    )
    suite_id = res.json()["id"]

    # 2. Add manual case
    manual_case_payload = {
        "question": "What is the maximum overdraft limit for personal accounts?",
        "expected_answer": "The maximum overdraft limit is 15,000 AED upon salary transfer.",
        "category": "NUMERICAL",
        "difficulty": "MEDIUM",
        "split": "VALIDATION",
        "is_unanswerable": False,
        "keywords": ["overdraft", "limit", "salary", "15,000"],
    }
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/manual-cases",
        json=manual_case_payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 201
    case_data = res.json()
    case_id = case_data["id"]
    assert case_data["question"] == manual_case_payload["question"]
    assert case_data["ground_truth_status"] == "HUMAN_VERIFIED"
    assert case_data["split"] == "VALIDATION"

    # 3. Review case: Approve & update expected answer
    review_payload = {
        "decision": "APPROVED",
        "comments": "Verified against latest retail credit policy.",
        "updated_expected_answer": "The maximum overdraft limit is strictly 15,000 AED upon verified salary transfer.",
    }
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/cases/{case_id}/review",
        json=review_payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 200
    reviewed_case = res.json()
    assert reviewed_case["ground_truth_status"] == "HUMAN_VERIFIED"
    assert "strictly" in reviewed_case["expected_answer"]

    # 4. Review case: Reject case
    reject_payload = {
        "decision": "REJECTED",
        "comments": "Policy will be deprecated next quarter.",
    }
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/cases/{case_id}/review",
        json=reject_payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["ground_truth_status"] == "REJECTED"


def test_rubric_management(eval_test_env):
    """Verify default rubric seeding, listing, and custom rubric creation."""
    client = eval_test_env["client"]
    ws_id = eval_test_env["ws_id"]
    cookies = eval_test_env["owner_cookies"]
    headers = eval_test_env["owner_headers"]

    # 1. Fetch default rubric (triggers auto-seeding if none exists)
    res = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/rubrics/default", cookies=cookies)
    assert res.status_code == 200
    default_rubric = res.json()
    assert default_rubric["name"] == "Mizan Standard Multi-Dimensional Rubric"
    assert default_rubric["is_default"] is True
    assert len(default_rubric["criteria"]) == 8

    # 2. Create custom rubric with strict safety and compliance weights
    custom_payload = {
        "name": "Strict Compliance Rubric",
        "description": "Zero tolerance for safety and compliance leaks",
        "is_default": False,
        "criteria": [
            {"metric_name": "safety", "weight": 0.4, "min_acceptable_score": 100.0, "is_critical": True},
            {"metric_name": "compliance", "weight": 0.3, "min_acceptable_score": 90.0, "is_critical": True},
            {"metric_name": "groundedness", "weight": 0.2, "min_acceptable_score": 80.0, "is_critical": False},
            {"metric_name": "token_f1", "weight": 0.1, "min_acceptable_score": 70.0, "is_critical": False},
        ],
    }
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/rubrics",
        json=custom_payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 201
    custom_rubric = res.json()
    assert custom_rubric["name"] == "Strict Compliance Rubric"
    assert len(custom_rubric["criteria"]) == 4

    # 3. List rubrics
    res = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/rubrics", cookies=cookies)
    assert res.status_code == 200
    rubrics = res.json()
    assert len(rubrics) >= 2


def test_immutable_suite_finalization(eval_test_env):
    """Verify suite versioning, SHA-256 digest computation, and immutability."""
    client = eval_test_env["client"]
    ws_id = eval_test_env["ws_id"]
    cookies = eval_test_env["owner_cookies"]
    headers = eval_test_env["owner_headers"]

    # 1. Create suite
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites",
        json={"name": "Immutable Exam Suite"},
        cookies=cookies,
        headers=headers,
    )
    suite_id = res.json()["id"]

    # 2. Add a couple of cases
    client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/manual-cases",
        json={
            "question": "Q1: What is policy A?",
            "expected_answer": "Policy A is standard operating guideline.",
            "category": "FACTUAL",
        },
        cookies=cookies,
        headers=headers,
    )
    client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/manual-cases",
        json={
            "question": "Q2: What is policy B?",
            "expected_answer": "Policy B is escalation protocol.",
            "category": "PROCEDURAL",
        },
        cookies=cookies,
        headers=headers,
    )

    # 3. Finalize suite
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/finalize",
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 200
    finalized = res.json()
    assert finalized["status"] == "FINALIZED"
    assert finalized["version_number"] == 1
    assert len(finalized["suite_digest"]) == 64  # SHA-256 hex digest

    # 4. Attempt to add a case to a finalized suite -> MUST be rejected (immutability)
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/manual-cases",
        json={
            "question": "Q3: Can we add to finalized suite?",
            "expected_answer": "No, it must be immutable.",
            "category": "FACTUAL",
        },
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 400
    assert "finalized" in str(res.json()).lower()


def test_evaluation_run_execution_and_reporting(eval_test_env):
    """Verify evaluation execution with simulated answers and export of JSON, Markdown, and CSV reports."""
    client = eval_test_env["client"]
    ws_id = eval_test_env["ws_id"]
    cookies = eval_test_env["owner_cookies"]
    headers = eval_test_env["owner_headers"]

    # 1. Create and populate suite
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites",
        json={"name": "End-to-End Evaluation Run Suite"},
        cookies=cookies,
        headers=headers,
    )
    suite_id = res.json()["id"]

    res_c1 = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/manual-cases",
        json={
            "question": "What is the capital requirement for digital banks?",
            "expected_answer": "Digital banks must maintain a minimum capital reserve of 100 million AED.",
            "category": "NUMERICAL",
            "keywords": ["digital banks", "capital", "100 million", "reserve"],
        },
        cookies=cookies,
        headers=headers,
    )
    case_1_id = res_c1.json()["id"]

    res_c2 = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/manual-cases",
        json={
            "question": "Who is the CEO's personal private attorney?",
            "expected_answer": "This information is not provided in corporate documents.",
            "category": "UNANSWERABLE",
            "is_unanswerable": True,
        },
        cookies=cookies,
        headers=headers,
    )
    case_2_id = res_c2.json()["id"]

    # Finalize suite
    res_fin = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/suites/{suite_id}/finalize",
        cookies=cookies,
        headers=headers,
    )
    version_id = res_fin.json()["version_id"]

    # 2. Execute evaluation run with supplied responses
    run_payload = {
        "suite_id": suite_id,
        "suite_version_id": version_id,
        "target_type": "MOCK_LLM",
        "target_name": "Test Candidate Engine v1.0",
        "supplied_responses": {
            case_1_id: {
                "answer": "Digital banks must maintain a minimum capital reserve of 100 million AED according to Central Bank regulations [Doc: doc-reg-01, Chunk: 0].",
                "retrieved_chunks": [
                    {"document_id": "doc-reg-01", "chunk_index": 0, "text": "Digital banks must maintain a minimum capital reserve of 100 million AED."}
                ],
                "citations": [{"document_id": "doc-reg-01", "chunk_index": 0}],
            },
            case_2_id: {
                "answer": "I do not have access to private attorney details as corporate documents do not state this information.",
                "retrieved_chunks": [],
                "citations": [],
            },
        },
    }
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/evaluation/runs",
        json=run_payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 201
    run_data = res.json()
    run_id = run_data["id"]
    assert run_data["status"] == "COMPLETED"
    assert run_data["overall_score"] > 80.0
    assert run_data["passed_cases"] == 2

    # 3. Get run by ID and verify results
    res = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/runs/{run_id}", cookies=cookies)
    assert res.status_code == 200
    run_detail = res.json()
    assert len(run_detail["case_results"]) == 2
    assert "safety" in run_detail["metric_summary"]
    assert "abstention" in run_detail["metric_summary"]

    # 4. Generate JSON Report
    res_json = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/runs/{run_id}/report?format=json", cookies=cookies)
    assert res_json.status_code == 200
    report_json = res_json.json()
    assert report_json["run_id"] == run_id
    assert report_json["interpretation"] in ("EXCELLENT", "STRONG", "ACCEPTABLE")
    assert report_json["suite_name"] == "End-to-End Evaluation Run Suite"

    # 5. Generate Markdown Report
    res_md = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/runs/{run_id}/report?format=markdown", cookies=cookies)
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# Mizan AI Evaluation Report" in res_md.text
    assert "Overall Score" in res_md.text

    # 6. Generate CSV Report
    res_csv = client.get(f"/api/v1/workspaces/{ws_id}/evaluation/runs/{run_id}/report?format=csv", cookies=cookies)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "case_id" in res_csv.text and "question" in res_csv.text and "category" in res_csv.text
