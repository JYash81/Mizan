"""Processing job tracking service."""

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.dataset import JobStatus, ProcessingJob


def get_job(db: Session, workspace_id: str, job_id: str) -> ProcessingJob | None:
    return db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id,
            ProcessingJob.workspace_id == workspace_id,
        )
    )


def list_jobs(
    db: Session,
    workspace_id: str,
    status: JobStatus | None = None,
    limit: int = 50,
) -> list[ProcessingJob]:
    stmt = select(ProcessingJob).where(ProcessingJob.workspace_id == workspace_id)
    if status is not None:
        stmt = stmt.where(ProcessingJob.status == status)
    stmt = stmt.order_by(desc(ProcessingJob.created_at)).limit(limit)
    return list(db.scalars(stmt).all())
