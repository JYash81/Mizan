"""Tests for Dataset, DatasetVersion, Document, and ProcessingJob schema models."""

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.dataset import (
    Dataset,
    DatasetStatus,
    DatasetVersion,
    DatasetVersionStatus,
    Document,
    DocumentFileType,
    ExtractionStatus,
    JobStatus,
    JobType,
    ProcessingJob,
)
from app.models.identity import AccountStatus, User
from app.models.organization import (
    Organization,
    OrganizationStatus,
    Workspace,
    WorkspaceStatus,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def test_setup(db: Session):
    user = User(
        email="data_lead@example.com",
        normalized_email="data_lead@example.com",
        password_hash="argon2id$mock$hash",
        full_name="Data Lead",
        status=AccountStatus.ACTIVE,
    )
    db.add(user)
    db.flush()

    org = Organization(
        name="Data Innovations LLC",
        slug="data-innovations",
        created_by=user.id,
        status=OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()

    ws = Workspace(
        organization_id=org.id,
        name="Knowledge Lab",
        slug="knowledge-lab",
        created_by=user.id,
        status=WorkspaceStatus.ACTIVE,
    )
    db.add(ws)
    db.commit()

    return {"user_id": user.id, "org_id": org.id, "ws_id": ws.id}


def test_dataset_creation_and_unique_slug(db: Session, test_setup):
    ws_id = test_setup["ws_id"]
    user_id = test_setup["user_id"]

    ds = Dataset(
        workspace_id=ws_id,
        name="HR Policies",
        slug="hr-policies",
        description="Employee manuals and benefits",
        status=DatasetStatus.ACTIVE,
        created_by=user_id,
    )
    db.add(ds)
    db.commit()

    assert ds.id is not None
    assert ds.created_at is not None

    # Duplicate slug in same workspace must fail
    duplicate_ds = Dataset(
        workspace_id=ws_id,
        name="HR Duplicate",
        slug="hr-policies",
        created_by=user_id,
    )
    db.add(duplicate_ds)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_dataset_version_and_document_cascade(db: Session, test_setup):
    ws_id = test_setup["ws_id"]
    user_id = test_setup["user_id"]

    ds = Dataset(
        workspace_id=ws_id,
        name="Finance Reports",
        slug="finance-reports",
        created_by=user_id,
    )
    db.add(ds)
    db.flush()

    ver = DatasetVersion(
        dataset_id=ds.id,
        version_number=1,
        name="v1",
        status=DatasetVersionStatus.DRAFT,
    )
    db.add(ver)
    db.flush()

    doc = Document(
        dataset_version_id=ver.id,
        workspace_id=ws_id,
        name="q3_results.pdf",
        file_type=DocumentFileType.PDF,
        mime_type="application/pdf",
        raw_file_key=f"{ws_id}/documents/{ver.id}/q3.pdf",
        raw_file_size_bytes=1024,
        raw_sha256="a" * 64,
        char_count=500,
        word_count=80,
        page_count=2,
        extraction_status=ExtractionStatus.COMPLETED,
    )
    db.add(doc)
    db.flush()

    job = ProcessingJob(
        workspace_id=ws_id,
        dataset_version_id=ver.id,
        document_id=doc.id,
        job_type=JobType.DOCUMENT_EXTRACTION,
        status=JobStatus.COMPLETED,
        progress_pct=100,
    )
    db.add(job)
    db.commit()

    ver_id = ver.id
    doc_id = doc.id

    # Query back
    saved_doc = db.scalar(select(Document).where(Document.id == doc_id))
    assert saved_doc is not None
    assert saved_doc.name == "q3_results.pdf"
    assert saved_doc.char_count == 500

    # Delete dataset -> cascade deletes version and document
    db.delete(ds)
    db.commit()

    assert db.scalar(select(DatasetVersion).where(DatasetVersion.id == ver_id)) is None
    assert db.scalar(select(Document).where(Document.id == doc_id)) is None
