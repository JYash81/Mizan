"""Repository for EvaluationSuite and EvaluationSuiteVersion."""

from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.evaluation import (
    EvaluationSuite,
    EvaluationSuiteVersion,
)


class SuiteRepository:
    def create_suite(self, db: Session, suite: EvaluationSuite) -> EvaluationSuite:
        db.add(suite)
        db.flush()
        return suite

    def get_suite(self, db: Session, workspace_id: str, suite_id: str) -> EvaluationSuite | None:
        return db.execute(
            select(EvaluationSuite).where(
                EvaluationSuite.id == suite_id,
                EvaluationSuite.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

    def get_suite_by_slug(self, db: Session, workspace_id: str, slug: str) -> EvaluationSuite | None:
        return db.execute(
            select(EvaluationSuite).where(
                EvaluationSuite.slug == slug,
                EvaluationSuite.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

    def list_suites(
        self, db: Session, workspace_id: str, skip: int = 0, limit: int = 50
    ) -> list[EvaluationSuite]:
        return list(
            db.execute(
                select(EvaluationSuite)
                .where(EvaluationSuite.workspace_id == workspace_id)
                .order_by(desc(EvaluationSuite.created_at))
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def count_suites(self, db: Session, workspace_id: str) -> int:
        return db.execute(
            select(func.count(EvaluationSuite.id)).where(EvaluationSuite.workspace_id == workspace_id)
        ).scalar_one() or 0

    def create_version(self, db: Session, version: EvaluationSuiteVersion) -> EvaluationSuiteVersion:
        db.add(version)
        db.flush()
        return version

    def get_version(self, db: Session, version_id: str) -> EvaluationSuiteVersion | None:
        return db.execute(
            select(EvaluationSuiteVersion).where(EvaluationSuiteVersion.id == version_id)
        ).scalar_one_or_none()

    def list_versions(self, db: Session, suite_id: str) -> list[EvaluationSuiteVersion]:
        return list(
            db.execute(
                select(EvaluationSuiteVersion)
                .where(EvaluationSuiteVersion.suite_id == suite_id)
                .order_by(desc(EvaluationSuiteVersion.version_number))
            )
            .scalars()
            .all()
        )

    def get_latest_version(self, db: Session, suite_id: str) -> EvaluationSuiteVersion | None:
        return db.execute(
            select(EvaluationSuiteVersion)
            .where(EvaluationSuiteVersion.suite_id == suite_id)
            .order_by(desc(EvaluationSuiteVersion.version_number))
            .limit(1)
        ).scalar_one_or_none()
