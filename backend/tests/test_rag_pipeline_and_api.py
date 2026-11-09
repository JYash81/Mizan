"""Integration tests for Mizan RAG Pipeline, Providers, Evaluation, and REST APIs."""

from __future__ import annotations

import tempfile
from unittest.mock import patch

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
from app.modules.rag.embeddings.mock_provider import MockEmbeddingProvider
from app.modules.rag.vector_store.qdrant_local import QdrantLocalVectorStore
from app.modules.storage import (
    LocalStorageProvider,
    set_storage_provider_override,
)
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def rag_test_env():
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
        full_name="Fatima Lead",
        email="fatima@mizan.ae",
        normalized_email="fatima@mizan.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add(owner)
    db.commit()

    owner_sess = session_service.create_session(db, owner.id)
    org, _ = organization_service.create_organization(db, owner.id, "Mizan Corp", "mizan-corp")
    ws, _ = workspace_service.create_workspace(db, org.id, owner.id, "AI Lab", "ai-lab")
    db.commit()

    yield {
        "client": client,
        "engine": engine,
        "owner": owner,
        "org_id": org.id,
        "ws_id": ws.id,
        "storage": storage,
        "owner_cookies": {"mizan_session": owner_sess.session_token},
        "owner_headers": {"X-CSRF-Token": owner_sess.csrf_token},
    }

    set_storage_provider_override(None)
    tmp_dir.cleanup()


def test_list_providers_endpoint(rag_test_env):
    """Verify GET /workspaces/{ws_id}/rag/providers returns registered free providers."""
    client = rag_test_env["client"]
    ws_id = rag_test_env["ws_id"]
    cookies = rag_test_env["owner_cookies"]

    res = client.get(f"/api/v1/workspaces/{ws_id}/rag/providers", cookies=cookies)
    assert res.status_code == 200
    providers = res.json()
    assert len(providers) >= 3
    names = {p["provider_name"] for p in providers}
    assert "mock" in names
    assert "ollama" in names
    assert "gemini_free" in names
    assert all(p["is_free"] is True for p in providers)


def test_rag_index_requires_gate1_approval(rag_test_env):
    """INVARIANT: Verify indexing an unapproved dataset version fails closed with HTTP 403."""
    client = rag_test_env["client"]
    ws_id = rag_test_env["ws_id"]
    cookies = rag_test_env["owner_cookies"]
    headers = rag_test_env["owner_headers"]
    engine = rag_test_env["engine"]

    # 1. Create dataset version via API
    ds_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets",
        json={"name": "Unapproved Dataset", "slug": "unapproved-ds"},
        cookies=cookies,
        headers=headers,
    )
    assert ds_resp.status_code == 201
    version_id = ds_resp.json()["version"]["id"]

    # Mark version READY without Gate 1 approval
    db = Session(engine, expire_on_commit=False)
    ver = db.query(DatasetVersion).filter_by(id=version_id).first()
    ver.status = DatasetVersionStatus.READY
    db.commit()

    # Attempt to index unapproved version
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/rag/index",
        json={"dataset_version_id": version_id},
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 403
    err = res.json()
    assert "Gate 1" in str(err)


def test_rag_full_lifecycle_index_query_and_eval(rag_test_env):
    """End-to-end integration: Create dataset -> Detect & Mask -> Gate 1 Approve -> Index -> Query -> Evaluate."""
    client = rag_test_env["client"]
    ws_id = rag_test_env["ws_id"]
    cookies = rag_test_env["owner_cookies"]
    headers = rag_test_env["owner_headers"]
    engine = rag_test_env["engine"]

    db = Session(engine, expire_on_commit=False)

    # 1. Create dataset and upload document
    ds_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets",
        json={"name": "Financial Policies", "slug": "fin-policies"},
        cookies=cookies,
        headers=headers,
    )
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["dataset"]["id"]
    version_id = ds_resp.json()["version"]["id"]

    policy_text = (
        "Mizan Corporation Financial Regulations.\n"
        "All corporate budget approvals exceeding 50000 AED require Senior Executive sign-off.\n"
        "Customer accounts must comply with Central Bank regulatory compliance and KYC standards.\n"
        "Contact the finance controller at finance@mizan.ae or phone 04 345 6789 for inquiries."
    )
    upload_res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
        files={"file": ("policy.txt", policy_text.encode("utf-8"), "text/plain")},
        cookies=cookies,
        headers=headers,
    )
    assert upload_res.status_code == 201

    # Mark version READY
    ver = db.query(DatasetVersion).filter_by(id=version_id).first()
    ver.status = DatasetVersionStatus.READY
    ver.content_hash = "hash_policy_123"
    db.commit()

    # 2. Run Masking
    run_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs",
        json={"dataset_id": dataset_id, "dataset_version_id": version_id},
        cookies=cookies,
        headers=headers,
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # 3. Gate 1 Human Approval via API
    approve_res = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{run_id}/gate1/approve",
        json={"decision_reason": "RAG retrieval and corporate policy question answering."},
        cookies=cookies,
        headers=headers,
    )
    assert approve_res.status_code == 201
    assert approve_res.json()["decision"] == "APPROVED"

    # 4. Use in-memory Qdrant and MockEmbedding for fast API testing
    in_memory_qdrant = QdrantLocalVectorStore(in_memory=True)
    mock_embedder = MockEmbeddingProvider()

    with (
        patch("app.api.v1.endpoints.rag.get_vector_store", return_value=in_memory_qdrant),
        patch("app.api.v1.endpoints.rag.get_embedding_provider", return_value=mock_embedder),
    ):
        # 5. Index the approved dataset version
        index_res = client.post(
            f"/api/v1/workspaces/{ws_id}/rag/index",
            json={"dataset_version_id": version_id, "chunk_size_chars": 200, "chunk_overlap_chars": 50},
            cookies=cookies,
            headers=headers,
        )
        assert index_res.status_code == 201
        idx_data = index_res.json()
        assert idx_data["chunks_indexed"] > 0
        assert idx_data["documents_indexed"] == 1
        assert idx_data["workspace_id"] == ws_id

        # 6. Query the indexed RAG pipeline
        query_res = client.post(
            f"/api/v1/workspaces/{ws_id}/rag/query",
            json={
                "query": "What is the requirement for corporate budget approvals exceeding 50000 AED?",
                "dataset_version_id": version_id,
                "provider": "mock",
                "top_k": 3,
                "score_threshold": 0.0,
            },
            cookies=cookies,
            headers=headers,
        )
        assert query_res.status_code == 200
        q_data = query_res.json()
        assert "Senior Executive sign-off" in q_data["answer"] or len(q_data["retrieved_chunks"]) > 0
        assert len(q_data["citations"]) > 0
        assert q_data["citations"][0]["citation_marker"].startswith("[Doc:")
        assert q_data["provider"]["name"] == "mock"
        assert q_data["metrics"]["cost_cents"] == 0.0

        # 7. Paid provider rejection via API
        paid_res = client.post(
            f"/api/v1/workspaces/{ws_id}/rag/query",
            json={
                "query": "Should fail with paid provider",
                "provider": "openai",
            },
            cookies=cookies,
            headers=headers,
        )
        assert paid_res.status_code == 403
        err_msg = paid_res.json().get("error", {}).get("message", "") or paid_res.json().get("detail", "")
        assert "cost policy" in err_msg.lower()

        # 8. Evaluate RAG execution
        eval_res = client.post(
            f"/api/v1/workspaces/{ws_id}/rag/evaluate",
            json={
                "query": q_data["query"],
                "answer": q_data["answer"],
                "retrieved_chunks": q_data["retrieved_chunks"],
                "expected_keywords": ["Senior Executive", "budget", "approvals"],
            },
            cookies=cookies,
        )
        assert eval_res.status_code == 200
        eval_data = eval_res.json()
        assert 0.0 <= eval_data["retrieval_recall"] <= 1.0
        assert 0.0 <= eval_data["context_relevance"] <= 1.0
        assert 0.0 <= eval_data["faithfulness"] <= 1.0
        assert 0.0 <= eval_data["citation_completeness"] <= 1.0
        assert 0.0 <= eval_data["overall_score"] <= 1.0
        assert eval_data["retrieved_chunks_count"] > 0

    in_memory_qdrant.close()
