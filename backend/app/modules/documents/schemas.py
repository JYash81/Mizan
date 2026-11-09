"""Pydantic schemas for Documents and Processing Jobs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: str
    dataset_version_id: str
    workspace_id: str
    name: str
    file_type: str
    mime_type: str
    raw_file_size_bytes: int
    raw_sha256: str
    extracted_text_sample: str | None
    char_count: int
    word_count: int
    page_count: int | None
    extraction_status: str
    extraction_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    extracted_text: str | None = None


class ProcessingJobResponse(BaseModel):
    id: str
    workspace_id: str
    dataset_version_id: str | None
    document_id: str | None
    job_type: str
    status: str
    progress_pct: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
