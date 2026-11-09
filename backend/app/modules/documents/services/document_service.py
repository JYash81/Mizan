"""Document ingestion, storage persistence, and text extraction service."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.dataset import (
    DatasetVersion,
    DatasetVersionStatus,
    Document,
    DocumentFileType,
    ExtractionStatus,
    JobStatus,
    JobType,
    ProcessingJob,
)
from app.modules.documents.parsers import parse_document
from app.modules.documents.services.file_validator import validate_file_upload
from app.modules.storage import StorageBucket, StorageProvider


class DocumentDuplicateError(Exception):
    """Raised when duplicate file content is uploaded to the same dataset version."""


def upload_document(
    db: Session,
    storage: StorageProvider,
    workspace_id: str,
    dataset_version_id: str,
    filename: str,
    content: bytes,
    actor_id: str,
    max_size_bytes: int = 25 * 1024 * 1024,
) -> tuple[Document, ProcessingJob]:
    """Validates file, persists binary to secure storage, and creates database records."""
    version = db.get(DatasetVersion, dataset_version_id)
    if version is None:
        raise ValueError(f"Dataset version {dataset_version_id} not found.")

    if version.status == DatasetVersionStatus.ARCHIVED:
        raise ValueError("Cannot add documents to an archived dataset version.")

    validated = validate_file_upload(filename, content, max_size_bytes=max_size_bytes)

    # Check for duplicate document in this version
    duplicate = db.scalar(
        select(Document).where(
            Document.dataset_version_id == dataset_version_id,
            Document.raw_sha256 == validated.sha256,
        )
    )
    if duplicate is not None:
        raise DocumentDuplicateError(
            f"File '{filename}' with hash {validated.sha256[:12]} already exists in this version as '{duplicate.name}'."
        )

    doc_id = str(uuid.uuid4())
    storage_key = f"{workspace_id}/raw_uploads/{dataset_version_id}/{doc_id}/{validated.filename}"

    # 1. Put raw bytes in storage
    storage.put_object(
        bucket=StorageBucket.RAW_UPLOADS,
        key=storage_key,
        data=validated.content,
        content_type=validated.mime_type,
    )

    # 2. Create document record
    doc = Document(
        id=doc_id,
        dataset_version_id=dataset_version_id,
        workspace_id=workspace_id,
        name=validated.filename,
        file_type=DocumentFileType(validated.file_type),
        mime_type=validated.mime_type,
        raw_file_key=storage_key,
        raw_file_size_bytes=validated.size_bytes,
        raw_sha256=validated.sha256,
        extraction_status=ExtractionStatus.PENDING,
    )
    db.add(doc)

    # 3. Create tracking job
    job = ProcessingJob(
        workspace_id=workspace_id,
        dataset_version_id=dataset_version_id,
        document_id=doc_id,
        job_type=JobType.DOCUMENT_EXTRACTION,
        status=JobStatus.PENDING,
        progress_pct=0,
    )
    db.add(job)
    db.commit()
    db.refresh(doc)
    db.refresh(job)

    # 4. Execute extraction immediately (bounded)
    process_document_extraction(db, storage, doc_id, job.id)
    db.refresh(doc)
    db.refresh(job)

    return doc, job


def process_document_extraction(
    db: Session,
    storage: StorageProvider,
    document_id: str,
    job_id: str | None = None,
) -> Document:
    """Extracts text and structure from raw document binary and updates records."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise ValueError(f"Document {document_id} not found.")

    job = db.get(ProcessingJob, job_id) if job_id else None
    if job:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        job.progress_pct = 25
        db.commit()

    doc.extraction_status = ExtractionStatus.PARSING
    db.commit()

    try:
        raw_data, _ = storage.get_object(StorageBucket.RAW_UPLOADS, doc.raw_file_key)
        if job:
            job.progress_pct = 50
            db.commit()

        # Parse with bounded dispatcher
        result = parse_document(doc.file_type, doc.name, raw_data)

        # Store full extracted text in storage if larger than 10KB
        extracted_text_key: str | None = None
        if len(result.text.encode("utf-8")) > 10_000:
            extracted_text_key = (
                f"{doc.workspace_id}/raw_uploads/{doc.dataset_version_id}/{doc.id}/extracted.txt"
            )
            storage.put_object(
                bucket=StorageBucket.RAW_UPLOADS,
                key=extracted_text_key,
                data=result.text.encode("utf-8"),
                content_type="text/plain; charset=utf-8",
            )

        doc.extracted_text_key = extracted_text_key
        doc.extracted_text_sample = result.sample
        doc.char_count = result.char_count
        doc.word_count = result.word_count
        doc.page_count = result.page_count
        doc.extraction_status = ExtractionStatus.COMPLETED
        doc.extraction_error = None

        if job:
            job.status = JobStatus.COMPLETED
            job.progress_pct = 100
            job.completed_at = datetime.now(UTC)
            job.error_message = None

        # Update dataset version stats
        version = db.get(DatasetVersion, doc.dataset_version_id)
        if version:
            version.total_documents = (
                db.scalar(
                    select(func.count(Document.id)).where(
                        Document.dataset_version_id == doc.dataset_version_id
                    )
                )
                or 0
            )
            version.total_raw_bytes = (
                db.scalar(
                    select(func.sum(Document.raw_file_size_bytes)).where(
                        Document.dataset_version_id == doc.dataset_version_id
                    )
                )
                or 0
            )

        db.commit()
        db.refresh(doc)
        return doc

    except Exception as e:
        doc.extraction_status = ExtractionStatus.FAILED
        doc.extraction_error = str(e)
        if job:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(UTC)
            job.error_message = str(e)
        db.commit()
        db.refresh(doc)
        return doc


def get_document(
    db: Session,
    workspace_id: str,
    document_id: str,
) -> Document | None:
    return db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )


def list_documents(
    db: Session,
    dataset_version_id: str,
) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.dataset_version_id == dataset_version_id)
            .order_by(desc(Document.created_at))
        ).all()
    )


def delete_document(
    db: Session,
    storage: StorageProvider,
    workspace_id: str,
    document_id: str,
) -> bool:
    doc = get_document(db, workspace_id, document_id)
    if doc is None:
        return False

    version_id = doc.dataset_version_id

    # 1. Delete physical files from storage
    storage.delete_object(StorageBucket.RAW_UPLOADS, doc.raw_file_key)
    if doc.extracted_text_key:
        storage.delete_object(StorageBucket.RAW_UPLOADS, doc.extracted_text_key)

    # 2. Delete document record
    db.delete(doc)
    db.flush()

    # 3. Update version counts
    version = db.get(DatasetVersion, version_id)
    if version:
        version.total_documents = (
            db.scalar(
                select(func.count(Document.id)).where(Document.dataset_version_id == version_id)
            )
            or 0
        )
        version.total_raw_bytes = (
            db.scalar(
                select(func.sum(Document.raw_file_size_bytes)).where(
                    Document.dataset_version_id == version_id
                )
            )
            or 0
        )

    db.commit()
    return True


def reprocess_document(
    db: Session,
    storage: StorageProvider,
    workspace_id: str,
    document_id: str,
) -> ProcessingJob:
    doc = get_document(db, workspace_id, document_id)
    if doc is None:
        raise ValueError(f"Document {document_id} not found.")

    job = ProcessingJob(
        workspace_id=workspace_id,
        dataset_version_id=doc.dataset_version_id,
        document_id=doc.id,
        job_type=JobType.DOCUMENT_EXTRACTION,
        status=JobStatus.PENDING,
        progress_pct=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    process_document_extraction(db, storage, doc.id, job.id)
    db.refresh(job)
    return job
