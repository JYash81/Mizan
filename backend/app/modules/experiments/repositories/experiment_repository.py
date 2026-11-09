"""Database repository for experiments, trials, and audit events."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.experiment import Experiment, ExperimentEvent, ExperimentTrial


class ExperimentRepository:
    """Repository handling persistence and queries for Milestone 7 experiment entities."""

    def create_experiment(self, db: Session, experiment: Experiment) -> Experiment:
        db.add(experiment)
        db.flush()
        return experiment

    def get_experiment(
        self, db: Session, experiment_id: str, workspace_id: str | None = None
    ) -> Experiment | None:
        stmt = select(Experiment).where(Experiment.id == experiment_id)
        if workspace_id:
            stmt = stmt.where(Experiment.workspace_id == workspace_id)
        return db.scalars(stmt).first()

    def get_experiment_by_slug(
        self, db: Session, workspace_id: str, slug: str
    ) -> Experiment | None:
        stmt = select(Experiment).where(
            Experiment.workspace_id == workspace_id, Experiment.slug == slug
        )
        return db.scalars(stmt).first()

    def list_experiments(
        self, db: Session, workspace_id: str, skip: int = 0, limit: int = 50
    ) -> list[Experiment]:
        stmt = (
            select(Experiment)
            .where(Experiment.workspace_id == workspace_id)
            .order_by(Experiment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    def count_experiments(self, db: Session, workspace_id: str) -> int:
        stmt = (
            select(func.count(Experiment.id))
            .where(Experiment.workspace_id == workspace_id)
        )
        return db.scalar(stmt) or 0

    def update_experiment(self, db: Session, experiment: Experiment) -> Experiment:
        db.flush()
        return experiment

    def add_trials(
        self, db: Session, trials: list[ExperimentTrial]
    ) -> list[ExperimentTrial]:
        for t in trials:
            db.add(t)
        db.flush()
        return trials

    def delete_trials(self, db: Session, experiment_id: str) -> None:
        stmt = select(ExperimentTrial).where(ExperimentTrial.experiment_id == experiment_id)
        for t in db.scalars(stmt).all():
            db.delete(t)
        db.flush()

    def list_trials(self, db: Session, experiment_id: str) -> list[ExperimentTrial]:
        stmt = (
            select(ExperimentTrial)
            .where(ExperimentTrial.experiment_id == experiment_id)
            .order_by(ExperimentTrial.trial_number.asc())
        )
        return list(db.scalars(stmt).all())

    def get_trial(
        self, db: Session, trial_id: str, experiment_id: str | None = None
    ) -> ExperimentTrial | None:
        stmt = select(ExperimentTrial).where(ExperimentTrial.id == trial_id)
        if experiment_id:
            stmt = stmt.where(ExperimentTrial.experiment_id == experiment_id)
        return db.scalars(stmt).first()

    def update_trial(self, db: Session, trial: ExperimentTrial) -> ExperimentTrial:
        db.flush()
        return trial

    def record_event(self, db: Session, event: ExperimentEvent) -> ExperimentEvent:
        db.add(event)
        db.flush()
        return event

    def list_events(self, db: Session, experiment_id: str) -> list[ExperimentEvent]:
        stmt = (
            select(ExperimentEvent)
            .where(ExperimentEvent.experiment_id == experiment_id)
            .order_by(ExperimentEvent.created_at.asc())
        )
        return list(db.scalars(stmt).all())
