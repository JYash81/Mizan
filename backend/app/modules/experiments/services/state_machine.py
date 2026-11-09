"""Deterministic state machine transitions for Mizan experiments and trials."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.experiment import (
    Experiment,
    ExperimentEvent,
    ExperimentStatus,
    ExperimentTrial,
    TrialStatus,
)
from app.modules.experiments.repositories.experiment_repository import ExperimentRepository

VALID_EXPERIMENT_TRANSITIONS: dict[ExperimentStatus, set[ExperimentStatus]] = {
    ExperimentStatus.DRAFT: {
        ExperimentStatus.VALIDATING,
        ExperimentStatus.READY,
        ExperimentStatus.CANCEL_REQUESTED,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.VALIDATING: {
        ExperimentStatus.READY,
        ExperimentStatus.DRAFT,
        ExperimentStatus.FAILED,
        ExperimentStatus.CANCEL_REQUESTED,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.READY: {
        ExperimentStatus.QUEUED,
        ExperimentStatus.RUNNING,
        ExperimentStatus.DRAFT,
        ExperimentStatus.CANCEL_REQUESTED,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.QUEUED: {
        ExperimentStatus.RUNNING,
        ExperimentStatus.CANCEL_REQUESTED,
        ExperimentStatus.CANCELLED,
        ExperimentStatus.FAILED,
    },
    ExperimentStatus.RUNNING: {
        ExperimentStatus.COMPLETED,
        ExperimentStatus.COMPLETED_WITH_ERRORS,
        ExperimentStatus.FAILED,
        ExperimentStatus.CANCEL_REQUESTED,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.CANCEL_REQUESTED: {
        ExperimentStatus.CANCELLED,
        ExperimentStatus.FAILED,
    },
    ExperimentStatus.COMPLETED: set(),
    ExperimentStatus.COMPLETED_WITH_ERRORS: set(),
    ExperimentStatus.FAILED: set(),
    ExperimentStatus.CANCELLED: set(),
}

VALID_TRIAL_TRANSITIONS: dict[TrialStatus, set[TrialStatus]] = {
    TrialStatus.PENDING: {
        TrialStatus.VALIDATING,
        TrialStatus.QUEUED,
        TrialStatus.RUNNING,
        TrialStatus.SKIPPED,
        TrialStatus.CANCEL_REQUESTED,
        TrialStatus.CANCELLED,
    },
    TrialStatus.VALIDATING: {
        TrialStatus.QUEUED,
        TrialStatus.RUNNING,
        TrialStatus.FAILED,
        TrialStatus.CANCEL_REQUESTED,
        TrialStatus.CANCELLED,
    },
    TrialStatus.QUEUED: {
        TrialStatus.RUNNING,
        TrialStatus.SKIPPED,
        TrialStatus.CANCEL_REQUESTED,
        TrialStatus.CANCELLED,
        TrialStatus.FAILED,
    },
    TrialStatus.RUNNING: {
        TrialStatus.COMPLETED,
        TrialStatus.FAILED,
        TrialStatus.CANCEL_REQUESTED,
        TrialStatus.CANCELLED,
    },
    TrialStatus.CANCEL_REQUESTED: {
        TrialStatus.CANCELLED,
        TrialStatus.FAILED,
    },
    TrialStatus.COMPLETED: set(),
    TrialStatus.FAILED: set(),
    TrialStatus.SKIPPED: set(),
    TrialStatus.CANCELLED: set(),
}


class ExperimentStateMachine:
    """Manages deterministic status transitions and audit logging for experiments and trials."""

    def __init__(self, repository: ExperimentRepository | None = None) -> None:
        self.repo = repository or ExperimentRepository()

    def transition_experiment(
        self,
        db: Session,
        experiment: Experiment,
        target_status: ExperimentStatus,
        actor_id: str | None = None,
        event_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> Experiment:
        """Validate and apply a state transition on an experiment."""
        current = experiment.status
        if current == target_status:
            return experiment

        allowed = VALID_EXPERIMENT_TRANSITIONS.get(current, set())
        if target_status not in allowed:
            raise ValueError(
                f"Invalid experiment state transition: cannot move from {current.value} to {target_status.value}."
            )

        now = datetime.now(UTC)
        experiment.status = target_status
        experiment.updated_at = now

        if target_status == ExperimentStatus.RUNNING and not experiment.started_at:
            experiment.started_at = now
        elif target_status in (
            ExperimentStatus.COMPLETED,
            ExperimentStatus.COMPLETED_WITH_ERRORS,
            ExperimentStatus.FAILED,
            ExperimentStatus.CANCELLED,
        ):
            if not experiment.completed_at:
                experiment.completed_at = now
        elif target_status == ExperimentStatus.CANCEL_REQUESTED:
            experiment.cancellation_requested_at = now

        self.repo.update_experiment(db, experiment)

        # Audit event
        evt_type = event_type or f"EXPERIMENT_{target_status.value}"
        meta = metadata.copy() if metadata else {}
        if message:
            meta["message"] = message

        event = ExperimentEvent(
            experiment_id=experiment.id,
            trial_id=None,
            event_type=evt_type,
            previous_status=current.value,
            new_status=target_status.value,
            actor_id=actor_id,
            metadata_json=json.dumps(meta) if meta else None,
            created_at=now,
        )
        self.repo.record_event(db, event)
        return experiment

    def transition_trial(
        self,
        db: Session,
        trial: ExperimentTrial,
        target_status: TrialStatus,
        actor_id: str | None = None,
        event_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> ExperimentTrial:
        """Validate and apply a state transition on an individual trial."""
        current = trial.status
        if current == target_status:
            return trial

        allowed = VALID_TRIAL_TRANSITIONS.get(current, set())
        if target_status not in allowed:
            raise ValueError(
                f"Invalid trial state transition: cannot move trial #{trial.trial_number} "
                f"from {current.value} to {target_status.value}."
            )

        now = datetime.now(UTC)
        trial.status = target_status
        trial.updated_at = now

        if target_status == TrialStatus.QUEUED and not trial.queued_at:
            trial.queued_at = now
        elif target_status == TrialStatus.RUNNING and not trial.started_at:
            trial.started_at = now
        elif target_status in (
            TrialStatus.COMPLETED,
            TrialStatus.FAILED,
            TrialStatus.SKIPPED,
            TrialStatus.CANCELLED,
        ):
            if not trial.completed_at:
                trial.completed_at = now

        self.repo.update_trial(db, trial)

        # Audit event
        evt_type = event_type or f"TRIAL_{target_status.value}"
        meta = metadata.copy() if metadata else {}
        if message:
            meta["message"] = message

        event = ExperimentEvent(
            experiment_id=trial.experiment_id,
            trial_id=trial.id,
            event_type=evt_type,
            previous_status=current.value,
            new_status=target_status.value,
            actor_id=actor_id,
            metadata_json=json.dumps(meta) if meta else None,
            created_at=now,
        )
        self.repo.record_event(db, event)
        return trial
