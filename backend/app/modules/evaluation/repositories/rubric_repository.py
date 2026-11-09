"""Repository for EvaluationRubric and RubricCriterion."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationRubric, RubricCriterion


class RubricRepository:
    def create_rubric(self, db: Session, rubric: EvaluationRubric) -> EvaluationRubric:
        db.add(rubric)
        db.flush()
        return rubric

    def get_rubric(self, db: Session, rubric_id: str, workspace_id: str | None = None) -> EvaluationRubric | None:
        query = select(EvaluationRubric).where(EvaluationRubric.id == rubric_id)
        if workspace_id:
            query = query.where(EvaluationRubric.workspace_id == workspace_id)
        return db.execute(query).scalar_one_or_none()

    def get_default_rubric(self, db: Session, workspace_id: str) -> EvaluationRubric | None:
        return db.execute(
            select(EvaluationRubric).where(
                EvaluationRubric.workspace_id == workspace_id,
                EvaluationRubric.is_default.is_(True),
            )
        ).scalar_one_or_none()

    def list_rubrics(
        self, db: Session, workspace_id: str, skip: int = 0, limit: int = 50
    ) -> list[EvaluationRubric]:
        return list(
            db.execute(
                select(EvaluationRubric)
                .where(EvaluationRubric.workspace_id == workspace_id)
                .order_by(desc(EvaluationRubric.created_at))
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def add_criteria(self, db: Session, criteria: list[RubricCriterion]) -> list[RubricCriterion]:
        db.add_all(criteria)
        db.flush()
        return criteria

    def list_criteria(self, db: Session, rubric_id: str) -> list[RubricCriterion]:
        return list(
            db.execute(
                select(RubricCriterion)
                .where(RubricCriterion.rubric_id == rubric_id)
                .order_by(RubricCriterion.created_at)
            )
            .scalars()
            .all()
        )
