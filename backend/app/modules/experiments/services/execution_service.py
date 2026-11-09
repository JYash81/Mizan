"""Experiment Execution Service for running bounded sequential trial matrices on local CPU.

INVARIANTS:
1. Concurrency: 1 (Sequential execution on local CPU to respect 8 GB RAM limit).
2. Gate 1 human approval strictly required for the dataset version.
3. Frozen evaluation suite required.
4. Fail-closed on unauthorized, unapproved, or corrupted configurations.
5. Failure isolation: Failure of an individual trial does not erase or fail other trials.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.v1.endpoints.rag import get_embedding_provider, get_vector_store
from app.models.evaluation import EvaluationRun, EvaluationTargetType, SplitType
from app.models.experiment import Experiment, ExperimentStatus, ExperimentTrial, TrialStatus
from app.modules.evaluation.repositories.run_repository import RunRepository
from app.modules.evaluation.repositories.suite_repository import SuiteRepository
from app.modules.evaluation.services.evaluation_service import EvaluationService
from app.modules.experiments.matrix.validator import validate_trial_matrix
from app.modules.experiments.repositories.experiment_repository import ExperimentRepository
from app.modules.experiments.services.state_machine import ExperimentStateMachine
from app.modules.masking.approval.gate1_service import require_gate1_approval
from app.modules.rag.embeddings.base import EmbeddingProvider
from app.modules.rag.pipeline.rag_service import index_approved_dataset_version
from app.modules.rag.providers.base import LLMProvider
from app.modules.rag.providers.registry import get_llm_provider
from app.modules.rag.vector_store.base import VectorStoreProvider
from app.modules.storage import StorageProvider, get_storage_provider

logger = logging.getLogger(__name__)


def compute_latencies(latencies: list[float]) -> tuple[float | None, float | None]:
    """Calculate p50 and p95 latencies from a list of measurements."""
    if not latencies:
        return None, None
    sorted_l = sorted(latencies)
    n = len(sorted_l)
    p50 = sorted_l[n // 2]
    p95_idx = min(int(n * 0.95), n - 1)
    p95 = sorted_l[p95_idx]
    return round(p50, 2), round(p95, 2)


class ExperimentExecutionService:
    def __init__(
        self,
        experiment_repo: ExperimentRepository | None = None,
        state_machine: ExperimentStateMachine | None = None,
        eval_service: EvaluationService | None = None,
        run_repo: RunRepository | None = None,
        suite_repo: SuiteRepository | None = None,
        storage: StorageProvider | None = None,
        vector_store: VectorStoreProvider | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.experiment_repo = experiment_repo or ExperimentRepository()
        self.state_machine = state_machine or ExperimentStateMachine(self.experiment_repo)
        self.eval_service = eval_service or EvaluationService()
        self.run_repo = run_repo or RunRepository()
        self.suite_repo = suite_repo or SuiteRepository()
        self._storage = storage
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider

    def _get_storage(self) -> StorageProvider:
        if self._storage is None:
            self._storage = get_storage_provider()
        return self._storage

    def _get_vector_store(self) -> VectorStoreProvider:
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    def _get_embedding_provider(self) -> EmbeddingProvider:
        if self._embedding_provider is None:
            self._embedding_provider = get_embedding_provider()
        return self._embedding_provider

    def execute_experiment(
        self,
        db: Session,
        workspace_id: str,
        experiment_id: str,
        actor_id: str,
        llm_provider_override: LLMProvider | None = None,
    ) -> Experiment:
        """Execute all trials in an experiment sequentially (concurrency: 1)."""
        experiment = self.experiment_repo.get_experiment(db, experiment_id, workspace_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found in workspace.")

        if experiment.status in {
            ExperimentStatus.COMPLETED,
            ExperimentStatus.COMPLETED_WITH_ERRORS,
            ExperimentStatus.CANCELLED,
            ExperimentStatus.FAILED,
        }:
            raise ValueError(
                f"Cannot execute experiment in terminal status '{experiment.status.value}'."
            )

        # 1. Reject Holdout split protection
        if experiment.evaluation_split == SplitType.HOLDOUT:
            raise ValueError(
                "Holdout evaluation split is protected and cannot be used for trial matrix tuning."
            )

        # 2. Gate 1 Human Approval validation (Strict fail-closed)
        storage = self._get_storage()
        require_gate1_approval(
            db=db,
            workspace_id=workspace_id,
            dataset_version_id=experiment.dataset_version_id,
            storage=storage,
        )

        # 3. Evaluation suite validation
        suite = self.suite_repo.get_suite(db, workspace_id, experiment.evaluation_suite_id)
        if not suite:
            raise ValueError(
                f"Evaluation suite {experiment.evaluation_suite_id} not found in workspace."
            )

        suite_version = None
        if experiment.evaluation_suite_version_id:
            suite_version = self.suite_repo.get_version(db, experiment.evaluation_suite_version_id)
        else:
            suite_version = self.suite_repo.get_latest_version(db, suite.id)
            if suite_version:
                experiment.evaluation_suite_version_id = suite_version.id

        if not suite_version:
            raise ValueError(
                f"Evaluation suite {suite.id} has no finalized/frozen version to execute against."
            )

        # 4. Validate trial matrix (3..9 unique trials)
        trials = self.experiment_repo.list_trials(db, experiment.id)
        trial_configs = [t.configuration for t in trials]
        validate_trial_matrix(trial_configs)

        # 5. Transition to RUNNING
        if experiment.status in {ExperimentStatus.DRAFT, ExperimentStatus.VALIDATING}:
            experiment = self.state_machine.transition_experiment(
                db, experiment, ExperimentStatus.READY, actor_id=actor_id
            )
        if experiment.status != ExperimentStatus.RUNNING:
            experiment = self.state_machine.transition_experiment(
                db, experiment, ExperimentStatus.RUNNING, actor_id=actor_id
            )
        experiment.started_at = datetime.now(UTC)
        db.commit()

        v_store = self._get_vector_store()
        embedder = self._get_embedding_provider()

        # 6. Sequential execution of trials (concurrency: 1)
        # Track indexed configurations to avoid redundant re-indexing for identical chunk parameters
        indexed_chunk_configs: set[tuple[int, int]] = set()

        for trial in trials:
            # Check for cancellation before starting trial
            db.refresh(experiment)
            if experiment.status == ExperimentStatus.CANCEL_REQUESTED:
                logger.info(
                    "Experiment %s cancellation requested. Aborting remaining trials.",
                    experiment.id,
                )
                self._cancel_remaining_trials(db, trials, actor_id)
                self.state_machine.transition_experiment(
                    db,
                    experiment,
                    ExperimentStatus.CANCELLED,
                    actor_id=actor_id,
                    message="Cancelled by user request.",
                )
                db.commit()
                return experiment

            # Transition trial to RUNNING
            self.state_machine.transition_trial(
                db, trial, TrialStatus.RUNNING, actor_id=actor_id
            )
            trial.started_at = datetime.now(UTC)
            db.commit()

            conf = trial.configuration
            chunk_size = conf.get("chunk_size", 500)
            chunk_overlap = conf.get("chunk_overlap", 100)
            top_k = conf.get("top_k", 4)
            score_threshold = conf.get("score_threshold", 0.0)
            provider_name = conf.get("provider_name", "mock")
            model_name = conf.get("model_name", "mock-rag-v1")
            system_prompt = conf.get("system_prompt", None)

            try:
                # Index dataset if this chunk configuration has not yet been indexed
                chunk_key = (chunk_size, chunk_overlap)
                if chunk_key not in indexed_chunk_configs:
                    index_approved_dataset_version(
                        db=db,
                        workspace_id=workspace_id,
                        dataset_version_id=experiment.dataset_version_id,
                        vector_store=v_store,
                        embedding_provider=embedder,
                        storage=storage,
                        chunk_size_chars=chunk_size,
                        chunk_overlap_chars=chunk_overlap,
                    )
                    indexed_chunk_configs.add(chunk_key)

                # Prepare LLM provider
                llm = llm_provider_override or get_llm_provider(provider_name)

                # Create M6 EvaluationRun for this trial
                retrieval_conf = {
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "top_k": top_k,
                    "score_threshold": score_threshold,
                    "system_prompt": system_prompt,
                }
                eval_run = EvaluationRun(
                    organization_id=experiment.organization_id,
                    workspace_id=workspace_id,
                    suite_id=experiment.evaluation_suite_id,
                    suite_version_id=experiment.evaluation_suite_version_id,
                    rubric_id=suite_version.rubric_id,
                    rubric_version=suite_version.rubric_version,
                    target_type=EvaluationTargetType.RAG_PIPELINE,
                    target_name=f"Trial-{trial.trial_number}-{model_name}",
                    provider_name=provider_name,
                    model_name=model_name,
                    retrieval_config_json=json.dumps(retrieval_conf),
                    total_cases=suite_version.case_count,
                    created_by=actor_id,
                )
                self.run_repo.create_run(db, eval_run)

                # Execute evaluation
                completed_run = self.eval_service.execute_evaluation_run(
                    db=db,
                    workspace_id=workspace_id,
                    run_id=eval_run.id,
                    vector_store=v_store,
                    embedding_provider=embedder,
                    llm_provider=llm,
                )

                # Compute latencies
                case_results = self.run_repo.list_case_results(db, completed_run.id)
                latencies = [cr.latency_ms for cr in case_results if cr.latency_ms is not None]
                p50, p95 = compute_latencies(latencies)

                trial.evaluation_run_id = completed_run.id
                trial.aggregate_score = completed_run.overall_score
                trial.score_breakdown_json = completed_run.score_breakdown_json
                trial.latency_p50_ms = p50
                trial.latency_p95_ms = p95
                trial.completed_at = datetime.now(UTC)

                if completed_run.completed_cases == 0 and completed_run.total_cases > 0:
                    trial.error_summary = "All evaluation cases failed during trial execution."
                    self.state_machine.transition_trial(
                        db,
                        trial,
                        TrialStatus.FAILED,
                        actor_id=actor_id,
                        message=f"Trial {trial.trial_number} failed: 0/{completed_run.total_cases} cases completed.",
                    )
                    experiment.failed_trials += 1
                else:
                    self.state_machine.transition_trial(
                        db,
                        trial,
                        TrialStatus.COMPLETED,
                        actor_id=actor_id,
                        message=f"Trial {trial.trial_number} completed with score {trial.aggregate_score}%",
                    )
                    experiment.completed_trials += 1
                db.commit()

            except Exception as exc:
                logger.error(
                    "Trial %d execution failed in experiment %s: %s",
                    trial.trial_number,
                    experiment.id,
                    exc,
                    exc_info=True,
                )
                trial.error_summary = str(exc)
                trial.completed_at = datetime.now(UTC)
                self.state_machine.transition_trial(
                    db,
                    trial,
                    TrialStatus.FAILED,
                    actor_id=actor_id,
                    message=f"Trial {trial.trial_number} failed: {exc}",
                )
                experiment.failed_trials += 1
                db.commit()

        # 7. Finalize experiment status
        db.refresh(experiment)
        if experiment.status == ExperimentStatus.CANCEL_REQUESTED:
            experiment = self.state_machine.transition_experiment(
                db, experiment, ExperimentStatus.CANCELLED, actor_id=actor_id
            )
        elif experiment.failed_trials > 0 and experiment.completed_trials > 0:
            experiment = self.state_machine.transition_experiment(
                db,
                experiment,
                ExperimentStatus.COMPLETED_WITH_ERRORS,
                actor_id=actor_id,
                message=f"Completed with {experiment.failed_trials} trial failure(s).",
            )
        elif experiment.failed_trials > 0 and experiment.completed_trials == 0:
            experiment = self.state_machine.transition_experiment(
                db,
                experiment,
                ExperimentStatus.FAILED,
                actor_id=actor_id,
                message="All trials failed.",
            )
        else:
            experiment = self.state_machine.transition_experiment(
                db,
                experiment,
                ExperimentStatus.COMPLETED,
                actor_id=actor_id,
                message="All trials completed successfully.",
            )

        experiment.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(experiment)
        return experiment

    def request_cancellation(
        self,
        db: Session,
        workspace_id: str,
        experiment_id: str,
        actor_id: str,
    ) -> Experiment:
        """Request graceful cancellation of a running or queued experiment."""
        experiment = self.experiment_repo.get_experiment(db, experiment_id, workspace_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found in workspace.")

        if experiment.status in {
            ExperimentStatus.COMPLETED,
            ExperimentStatus.COMPLETED_WITH_ERRORS,
            ExperimentStatus.CANCELLED,
            ExperimentStatus.FAILED,
        }:
            raise ValueError(
                f"Cannot cancel experiment in terminal status '{experiment.status.value}'."
            )

        if experiment.status in {
            ExperimentStatus.DRAFT,
            ExperimentStatus.VALIDATING,
            ExperimentStatus.READY,
            ExperimentStatus.QUEUED,
        }:
            # Immediately transition to CANCELLED
            trials = self.experiment_repo.list_trials(db, experiment.id)
            self._cancel_remaining_trials(db, trials, actor_id)
            experiment = self.state_machine.transition_experiment(
                db,
                experiment,
                ExperimentStatus.CANCELLED,
                actor_id=actor_id,
                message="Experiment cancelled before execution.",
            )
            experiment.completed_at = datetime.now(UTC)
            db.commit()
            return experiment

        # If RUNNING, mark CANCEL_REQUESTED so the sequential runner stops at next boundary
        experiment = self.state_machine.transition_experiment(
            db,
            experiment,
            ExperimentStatus.CANCEL_REQUESTED,
            actor_id=actor_id,
            message="Cancellation requested during execution.",
        )
        db.commit()
        return experiment

    def _cancel_remaining_trials(
        self, db: Session, trials: list[ExperimentTrial], actor_id: str
    ) -> None:
        """Mark all pending or queued trials as CANCELLED."""
        for t in trials:
            if t.status in {TrialStatus.PENDING, TrialStatus.QUEUED, TrialStatus.VALIDATING}:
                self.state_machine.transition_trial(
                    db,
                    t,
                    TrialStatus.CANCELLED,
                    actor_id=actor_id,
                    message="Cancelled by user.",
                )
