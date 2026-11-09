"""Repository for EvaluationRun, EvaluationCaseResult, and EvaluationMetricResult."""

from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.evaluation import (
    EvaluationCaseResult,
    EvaluationMetricResult,
    EvaluationRun,
)


class RunRepository:
    def create_run(self, db: Session, run: EvaluationRun) -> EvaluationRun:
        db.add(run)
        db.flush()
        return run

    def get_run(self, db: Session, run_id: str, workspace_id: str | None = None) -> EvaluationRun | None:
        query = select(EvaluationRun).where(EvaluationRun.id == run_id)
        if workspace_id:
            query = query.where(EvaluationRun.workspace_id == workspace_id)
        return db.execute(query).scalar_one_or_none()

    def list_runs(
        self,
        db: Session,
        workspace_id: str,
        suite_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[EvaluationRun]:
        query = select(EvaluationRun).where(EvaluationRun.workspace_id == workspace_id)
        if suite_id:
            query = query.where(EvaluationRun.suite_id == suite_id)
        query = query.order_by(desc(EvaluationRun.created_at)).offset(skip).limit(limit)
        return list(db.execute(query).scalars().all())

    def count_runs(self, db: Session, workspace_id: str) -> int:
        return db.execute(
            select(func.count(EvaluationRun.id)).where(EvaluationRun.workspace_id == workspace_id)
        ).scalar_one() or 0

    def add_case_result(self, db: Session, result: EvaluationCaseResult) -> EvaluationCaseResult:
        db.add(result)
        db.flush()
        return result

    def add_case_results_batch(
        self, db: Session, results: list[EvaluationCaseResult]
    ) -> list[EvaluationCaseResult]:
        db.add_all(results)
        db.flush()
        return results

    def list_case_results(self, db: Session, run_id: str) -> list[EvaluationCaseResult]:
        return list(
            db.execute(
                select(EvaluationCaseResult)
                .where(EvaluationCaseResult.run_id == run_id)
                .order_by(EvaluationCaseResult.created_at)
            )
            .scalars()
            .all()
        )

    def add_metric_results_batch(
        self, db: Session, metrics: list[EvaluationMetricResult]
    ) -> list[EvaluationMetricResult]:
        db.add_all(metrics)
        db.flush()
        return metrics

    def list_metric_results_for_case_result(
        self, db: Session, case_result_id: str
    ) -> list[EvaluationMetricResult]:
        return list(
            db.execute(
                select(EvaluationMetricResult)
                .where(EvaluationMetricResult.case_result_id == case_result_id)
                .order_by(EvaluationMetricResult.metric_key)
            )
            .scalars()
            .all()
        )
