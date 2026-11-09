"""Experiment Orchestration and Trial Matrix module (Milestone 7)."""

from app.modules.experiments.digest import compute_canonical_config_digest
from app.modules.experiments.matrix.generator import TrialMatrixGenerator
from app.modules.experiments.matrix.validator import validate_trial_matrix
from app.modules.experiments.repositories.experiment_repository import ExperimentRepository
from app.modules.experiments.services.comparison_service import ExperimentComparisonService
from app.modules.experiments.services.execution_service import ExperimentExecutionService
from app.modules.experiments.services.report_service import ExperimentReportService
from app.modules.experiments.services.state_machine import ExperimentStateMachine

__all__ = [
    "compute_canonical_config_digest",
    "TrialMatrixGenerator",
    "validate_trial_matrix",
    "ExperimentRepository",
    "ExperimentStateMachine",
    "ExperimentExecutionService",
    "ExperimentComparisonService",
    "ExperimentReportService",
]
