"""Integration tests for Dataset and Document management APIs."""

import io
import tempfile

import pytest
from docx import Document as DocxDoc
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.identity import AccountStatus, User
from app.modules.auth.services import password_service, session_service
from app.modules.storage import (
    LocalStorageProvider,
    set_storage_provider_override,
)
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def dataset_test_env():
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

    # Temp storage
    tmp_dir = tempfile.TemporaryDirectory()
    storage = LocalStorageProvider(tmp_dir.name)
    set_storage_provider_override(storage)

    client = TestClient(app)

    db = Session(engine, expire_on_commit=False)
    user = User(
        full_name="Sarah DataLead",
        email="sarah@corp.com",
        normalized_email="sarah@corp.com",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add(user)
    db.commit()

    # Create session
    sess = session_service.create_session(db, user.id)
    db.commit()

    # Create Org and Workspace
    org, _ = organization_service.create_organization(db, user.id, "Data Dynamics", "data-dynamics")
    ws, _ = workspace_service.create_workspace(db, org.id, user.id, "AI Knowledge", "ai-knowledge")

    ws_id = ws.id
    org_id = org.id
    user_id = user.id

    yield {
        "client": client,
        "user_id": user_id,
        "org_id": org_id,
        "ws_id": ws_id,
        "cookies": {"mizan_session": sess.session_token},
        "headers": {"X-CSRF-Token": sess.csrf_token},
    }

    set_storage_provider_override(None)
    tmp_dir.cleanup()


def test_dataset_and_document_full_lifecycle(dataset_test_env):
    client = dataset_test_env["client"]
    ws_id = dataset_test_env["ws_id"]
    cookies = dataset_test_env["cookies"]
    headers = dataset_test_env["headers"]

    # 1. Create a dataset
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets",
        cookies=cookies,
        headers=headers,
        json={
            "name": "HR Handbooks",
            "slug": "hr-handbooks",
            "description": "Company policies and onboarding documentation",
        },
    )
    assert res.status_code == 201
    data = res.json()
    dataset_id = data["dataset"]["id"]
    version_id = data["version"]["id"]
    assert data["dataset"]["name"] == "HR Handbooks"
    assert data["version"]["version_number"] == 1
    assert data["version"]["status"] == "DRAFT"

    # 2. List datasets in workspace
    res = client.get(
        f"/api/v1/workspaces/{ws_id}/datasets",
        cookies=cookies,
    )
    assert res.status_code == 200
    datasets = res.json()["datasets"]
    assert len(datasets) == 1
    assert datasets[0]["id"] == dataset_id
    assert datasets[0]["active_version"]["id"] == version_id

    # 3. Get dataset detail
    res = client.get(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}",
        cookies=cookies,
    )
    assert res.status_code == 200
    assert res.json()["dataset"]["slug"] == "hr-handbooks"

    # 4. Update dataset
    res = client.patch(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}",
        cookies=cookies,
        headers=headers,
        json={"name": "HR Global Policies", "description": "Updated description"},
    )
    assert res.status_code == 200
    assert res.json()["dataset"]["name"] == "HR Global Policies"

    # 5. Upload document (TXT)
    txt_content = b"All employees are entitled to 25 days annual leave."
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
        cookies=cookies,
        headers=headers,
        files={"file": ("annual_leave.txt", txt_content, "text/plain")},
    )
    assert res.status_code == 201
    doc_data = res.json()["document"]
    txt_doc_id = doc_data["id"]
    assert doc_data["file_type"] == "TXT"
    assert doc_data["extraction_status"] == "COMPLETED"
    assert doc_data["word_count"] == 9
    assert "annual leave" in doc_data["extracted_text_sample"]

    # 6. Upload duplicate document (Must fail with 409 Conflict)
    dup_res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
        cookies=cookies,
        headers=headers,
        files={"file": ("annual_leave_copy.txt", txt_content, "text/plain")},
    )
    assert dup_res.status_code == 409

    # 7. Upload DOCX document
    docx = DocxDoc()
    docx.add_heading("Code of Conduct", level=1)
    docx.add_paragraph("Integrity and confidentiality are foundational principles.")
    buf = io.BytesIO()
    docx.save(buf)

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
        cookies=cookies,
        headers=headers,
        files={
            "file": (
                "conduct.docx",
                buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert res.status_code == 201
    docx_doc = res.json()["document"]
    assert docx_doc["id"] is not None
    assert docx_doc["file_type"] == "DOCX"
    assert docx_doc["extraction_status"] == "COMPLETED"

    # 8. List documents in version
    res = client.get(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents",
        cookies=cookies,
    )
    assert res.status_code == 200
    docs = res.json()["documents"]
    assert len(docs) == 2

    # 9. Get single document detail with preview
    res = client.get(
        f"/api/v1/workspaces/{ws_id}/documents/{txt_doc_id}",
        cookies=cookies,
    )
    assert res.status_code == 200
    assert "All employees are entitled" in res.json()["document"]["extracted_text"]

    # 10. Finalize dataset version (freeze/compile)
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/finalize",
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 200
    finalized_ver = res.json()["version"]
    assert finalized_ver["status"] == "READY"
    assert finalized_ver["total_documents"] == 2
    assert finalized_ver["content_hash"] is not None
    assert len(finalized_ver["content_hash"]) == 64

    # 11. Create a new version (v2)
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions",
        cookies=cookies,
        headers=headers,
        json={"name": "v2", "description": "Second edition"},
    )
    assert res.status_code == 201
    v2_data = res.json()["version"]
    assert v2_data["version_number"] == 2
    assert v2_data["status"] == "DRAFT"

    # 12. Reprocess document
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/documents/{txt_doc_id}/reprocess",
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["job"]["status"] == "COMPLETED"

    # 13. Delete document
    res = client.delete(
        f"/api/v1/workspaces/{ws_id}/documents/{txt_doc_id}",
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 200

    # 14. Archive dataset
    res = client.delete(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}",
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["dataset"]["status"] == "ARCHIVED"
