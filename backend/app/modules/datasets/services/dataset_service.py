"""Dataset and DatasetVersion management service."""

import hashlib
import re

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.dataset import (
    Dataset,
    DatasetStatus,
    DatasetVersion,
    DatasetVersionStatus,
    Document,
)
from app.models.organization import Workspace, WorkspaceStatus
from app.modules.audit.services.audit_service import record_audit_event

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def generate_slug(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    slug = re.sub(r"[\s_-]+", "-", cleaned)
    return slug[:100] or "dataset"


def validate_slug(slug: str) -> str:
    cleaned = slug.strip().lower()
    if not cleaned or len(cleaned) < 2 or len(cleaned) > 120:
        raise ValueError("Slug must be between 2 and 120 characters.")
    if not SLUG_PATTERN.match(cleaned):
        raise ValueError("Slug must contain only lowercase alphanumeric characters and hyphens.")
    return cleaned


def create_dataset(
    db: Session,
    workspace_id: str,
    creator_id: str,
    name: str,
    description: str | None = None,
    slug: str | None = None,
) -> tuple[Dataset, DatasetVersion]:
    """Creates a new Dataset within a Workspace and initializes version 1."""
    ws = db.get(Workspace, workspace_id)
    if ws is None or ws.status == WorkspaceStatus.ARCHIVED:
        raise ValueError(f"Workspace {workspace_id} not found or archived.")

    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Dataset name cannot be blank.")

    final_slug = validate_slug(slug or generate_slug(cleaned_name))

    existing = db.scalar(
        select(Dataset).where(
            Dataset.workspace_id == workspace_id,
            Dataset.slug == final_slug,
        )
    )
    if existing is not None:
        raise ValueError(f"A dataset with slug '{final_slug}' already exists in this workspace.")

    dataset = Dataset(
        workspace_id=workspace_id,
        name=cleaned_name,
        slug=final_slug,
        description=description.strip() if description else None,
        status=DatasetStatus.ACTIVE,
        created_by=creator_id,
    )
    db.add(dataset)
    db.flush()

    # Create initial Draft Version 1
    version = DatasetVersion(
        dataset_id=dataset.id,
        version_number=1,
        name="v1",
        description="Initial dataset version",
        status=DatasetVersionStatus.DRAFT,
    )
    db.add(version)
    db.commit()
    db.refresh(dataset)
    db.refresh(version)

    record_audit_event(
        db=db,
        event_type="DATASET_CREATED",
        resource_type="dataset",
        resource_id=dataset.id,
        actor_user_id=creator_id,
        safe_metadata={
            "workspace_id": workspace_id,
            "dataset_name": dataset.name,
            "slug": dataset.slug,
            "initial_version_id": version.id,
        },
    )

    return dataset, version


def list_datasets(
    db: Session,
    workspace_id: str,
    include_archived: bool = False,
) -> list[Dataset]:
    stmt = select(Dataset).where(Dataset.workspace_id == workspace_id)
    if not include_archived:
        stmt = stmt.where(Dataset.status == DatasetStatus.ACTIVE)
    stmt = stmt.order_by(desc(Dataset.created_at))
    return list(db.scalars(stmt).all())


def get_dataset(
    db: Session,
    workspace_id: str,
    dataset_id: str,
) -> Dataset | None:
    return db.scalar(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.workspace_id == workspace_id,
        )
    )


def update_dataset(
    db: Session,
    workspace_id: str,
    dataset_id: str,
    name: str | None = None,
    description: str | None = None,
) -> Dataset:
    dataset = get_dataset(db, workspace_id, dataset_id)
    if dataset is None:
        raise ValueError("Dataset not found.")

    if name is not None:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Dataset name cannot be blank.")
        dataset.name = cleaned_name

    if description is not None:
        dataset.description = description.strip() if description else None

    db.commit()
    db.refresh(dataset)
    return dataset


def archive_dataset(
    db: Session,
    workspace_id: str,
    dataset_id: str,
) -> Dataset:
    dataset = get_dataset(db, workspace_id, dataset_id)
    if dataset is None:
        raise ValueError("Dataset not found.")

    dataset.status = DatasetStatus.ARCHIVED
    db.commit()
    db.refresh(dataset)
    return dataset


def create_dataset_version(
    db: Session,
    workspace_id: str,
    dataset_id: str,
    name: str | None = None,
    description: str | None = None,
) -> DatasetVersion:
    dataset = get_dataset(db, workspace_id, dataset_id)
    if dataset is None:
        raise ValueError("Dataset not found.")

    # Find highest version number
    max_num = (
        db.scalar(
            select(func.max(DatasetVersion.version_number)).where(
                DatasetVersion.dataset_id == dataset_id
            )
        )
        or 0
    )

    next_num = max_num + 1
    version_name = name.strip() if name else f"v{next_num}"

    new_version = DatasetVersion(
        dataset_id=dataset_id,
        version_number=next_num,
        name=version_name,
        description=description.strip() if description else None,
        status=DatasetVersionStatus.DRAFT,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


def list_dataset_versions(
    db: Session,
    dataset_id: str,
) -> list[DatasetVersion]:
    return list(
        db.scalars(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(desc(DatasetVersion.version_number))
        ).all()
    )


def get_dataset_version(
    db: Session,
    dataset_id: str,
    version_id: str,
) -> DatasetVersion | None:
    return db.scalar(
        select(DatasetVersion).where(
            DatasetVersion.id == version_id,
            DatasetVersion.dataset_id == dataset_id,
        )
    )


def finalize_dataset_version(
    db: Session,
    workspace_id: str,
    dataset_id: str,
    version_id: str,
) -> DatasetVersion:
    """Computes aggregated content hash across all completed documents and marks version READY."""
    version = get_dataset_version(db, dataset_id, version_id)
    if version is None:
        raise ValueError("Dataset version not found.")

    documents = list(
        db.scalars(
            select(Document)
            .where(Document.dataset_version_id == version_id)
            .order_by(Document.name)
        ).all()
    )

    total_docs = len(documents)
    total_bytes = sum(doc.raw_file_size_bytes for doc in documents)

    # Compute deterministic cumulative hash
    hasher = hashlib.sha256()
    for doc in documents:
        hasher.update(doc.raw_sha256.encode("ascii"))
    cumulative_hash = hasher.hexdigest() if total_docs > 0 else None

    version.total_documents = total_docs
    version.total_raw_bytes = total_bytes
    version.content_hash = cumulative_hash
    version.status = DatasetVersionStatus.READY

    db.commit()
    db.refresh(version)
    return version
