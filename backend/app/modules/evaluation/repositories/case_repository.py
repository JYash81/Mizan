"""Repository for EvaluationCase and EvaluationReview."""

from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.evaluation import (
    EvaluationCase,
    EvaluationReview,
    GroundTruthStatus,
    SplitType,
)


class CaseRepository:
    def create_case(self, db: Session, case: EvaluationCase) -> EvaluationCase:
        db.add(case)
        db.flush()
        return case

    def create_cases_batch(self, db: Session, cases: list[EvaluationCase]) -> list[EvaluationCase]:
        db.add_all(cases)
        db.flush()
        return cases

    def get_case(self, db: Session, case_id: str, workspace_id: str | None = None) -> EvaluationCase | None:
        query = select(EvaluationCase).where(EvaluationCase.id == case_id)
        if workspace_id:
            query = query.where(EvaluationCase.workspace_id == workspace_id)
        return db.execute(query).scalar_one_or_none()

    def list_cases_for_suite(
        self,
        db: Session,
        suite_id: str,
        suite_version_id: str | None = None,
        split: SplitType | None = None,
        ground_truth_status: GroundTruthStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EvaluationCase]:
        query = select(EvaluationCase).where(EvaluationCase.suite_id == suite_id)
        if suite_version_id is not None:
            query = query.where(EvaluationCase.suite_version_id == suite_version_id)
        if split is not None:
            query = query.where(EvaluationCase.split == split)
        if ground_truth_status is not None:
            query = query.where(EvaluationCase.ground_truth_status == ground_truth_status)

        query = query.order_by(EvaluationCase.created_at).offset(skip).limit(limit)
        return list(db.execute(query).scalars().all())

    def count_cases_for_suite(
        self,
        db: Session,
        suite_id: str,
        suite_version_id: str | None = None,
    ) -> int:
        query = select(func.count(EvaluationCase.id)).where(EvaluationCase.suite_id == suite_id)
        if suite_version_id is not None:
            query = query.where(EvaluationCase.suite_version_id == suite_version_id)
        return db.execute(query).scalar_one() or 0

    def create_review(self, db: Session, review: EvaluationReview) -> EvaluationReview:
        db.add(review)
        db.flush()
        return review

    def list_reviews_for_case(self, db: Session, case_id: str) -> list[EvaluationReview]:
        return list(
            db.execute(
                select(EvaluationReview)
                .where(EvaluationReview.case_id == case_id)
                .order_by(desc(EvaluationReview.created_at))
            )
            .scalars()
            .all()
        )
