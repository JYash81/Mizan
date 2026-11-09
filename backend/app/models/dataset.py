import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class DatasetStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class DatasetVersionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class DocumentFileType(str, enum.Enum):
    PDF = "PDF"
    DOCX = "DOCX"
    XLSX = "XLSX"
    CSV = "CSV"
    TXT = "TXT"
    JSON = "JSON"
    JSONL = "JSONL"
    IMAGE = "IMAGE"


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARSING = "PARSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobType(str, enum.Enum):
    DOCUMENT_EXTRACTION = "DOCUMENT_EXTRACTION"
    VERSION_COMPILATION = "VERSION_COMPILATION"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


DATASET_STATUS = Enum(
    DatasetStatus,
    native_enum=False,
    create_constraint=True,
    name="dataset_status",
)
DATASET_VERSION_STATUS = Enum(
    DatasetVersionStatus,
    native_enum=False,
    create_constraint=True,
    name="dataset_version_status",
)
DOCUMENT_FILE_TYPE = Enum(
    DocumentFileType,
    native_enum=False,
    create_constraint=True,
    name="document_file_type",
)
EXTRACTION_STATUS = Enum(
    ExtractionStatus,
    native_enum=False,
    create_constraint=True,
    name="extraction_status",
)
JOB_TYPE = Enum(
    JobType,
    native_enum=False,
    create_constraint=True,
    name="job_type",
)
JOB_STATUS = Enum(
    JobStatus,
    native_enum=False,
    create_constraint=True,
    name="job_status",
)


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (UniqueConstraint("workspace_id", "slug", name="uq_dataset_workspace_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DatasetStatus] = mapped_column(DATASET_STATUS, default=DatasetStatus.ACTIVE)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version_number", name="uq_dataset_version_num"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DatasetVersionStatus] = mapped_column(
        DATASET_VERSION_STATUS, default=DatasetVersionStatus.DRAFT
    )
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    total_raw_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    dataset_version_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[DocumentFileType] = mapped_column(DOCUMENT_FILE_TYPE)
    mime_type: Mapped[str] = mapped_column(String(120))
    raw_file_key: Mapped[str] = mapped_column(String(512))
    raw_file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    raw_sha256: Mapped[str] = mapped_column(String(64), index=True)
    extracted_text_key: Mapped[str | None] = mapped_column(String(512))
    extracted_text_sample: Mapped[str | None] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        EXTRACTION_STATUS, default=ExtractionStatus.PENDING
    )
    extraction_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    dataset_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="SET NULL"), index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    job_type: Mapped[JobType] = mapped_column(JOB_TYPE)
    status: Mapped[JobStatus] = mapped_column(JOB_STATUS, default=JobStatus.PENDING, index=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
