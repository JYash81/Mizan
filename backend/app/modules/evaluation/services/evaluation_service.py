"""Evaluation Execution Service orchestrating reproducible suite runs and rubric assessments."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.evaluation import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationMetricResult,
    EvaluationRubric,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationSuiteStatus,
    EvaluationSuiteVersion,
    EvaluationTargetType,
    MetricStatus,
    SuiteVersionStatus,
)
from app.modules.evaluation.evaluators.registry import (
    get_evaluator_by_key,
    get_evaluator_by_method,
)
from app.modules.evaluation.repositories.case_repository import CaseRepository
from app.modules.evaluation.repositories.rubric_repository import RubricRepository
from app.modules.evaluation.repositories.run_repository import RunRepository
from app.modules.evaluation.repositories.suite_repository import SuiteRepository
from app.modules.evaluation.services.rubric_service import RubricService
from app.modules.rag.embeddings.base import EmbeddingProvider
from app.modules.rag.pipeline.rag_service import query_rag
from app.modules.rag.providers.base import LLMProvider
from app.modules.rag.vector_store.base import VectorStoreProvider

logger = logging.getLogger(__name__)


def compute_suite_digest(cases: list[EvaluationCase]) -> str:
    """Calculate deterministic canonical SHA-256 digest over sorted evaluation cases."""
    sorted_cases = sorted(cases, key=lambda c: (c.category.value, c.difficulty.value, c.question))
    records = []
    for c in sorted_cases:
        records.append(
            {
                "id": c.id,
                "category": c.category.value,
                "difficulty": c.difficulty.value,
                "split": c.split.value,
                "language": c.language,
                "question": c.question,
                "expected_answer": c.expected_answer,
                "is_unanswerable": c.is_unanswerable,
            }
        )
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class EvaluationService:
    def __init__(
        self,
        suite_repo: SuiteRepository | None = None,
        case_repo: CaseRepository | None = None,
        rubric_repo: RubricRepository | None = None,
        run_repo: RunRepository | None = None,
        rubric_service: RubricService | None = None,
    ):
        self.suite_repo = suite_repo or SuiteRepository()
        self.case_repo = case_repo or CaseRepository()
        self.rubric_repo = rubric_repo or RubricRepository()
        self.run_repo = run_repo or RunRepository()
        self.rubric_service = rubric_service or RubricService(self.rubric_repo)

    def finalize_suite_version(
        self,
        db: Session,
        workspace_id: str,
        suite_id: str,
        actor_id: str,
        rubric_id: str | None = None,
    ) -> EvaluationSuiteVersion:
        """Freeze evaluation suite cases into an immutable, versioned, digest-attested snapshot."""
        suite = self.suite_repo.get_suite(db, workspace_id, suite_id)
        if not suite:
            raise ValueError(f"EvaluationSuite {suite_id} not found in workspace.")

        # Load all unversioned cases for this suite
        cases = self.case_repo.list_cases_for_suite(db, suite.id, suite_version_id=None, limit=500)
        if not cases:
            # Check if any cases exist overall
            all_cases = self.case_repo.list_cases_for_suite(db, suite.id, limit=500)
            if not all_cases:
                raise ValueError("Cannot finalize evaluation suite: No examination cases exist.")
            cases = all_cases

        latest_ver = self.suite_repo.get_latest_version(db, suite.id)
        next_ver_num = (latest_ver.version_number + 1) if latest_ver else 1

        digest = compute_suite_digest(cases)

        # Resolve rubric
        rubric: EvaluationRubric
        if rubric_id:
            r = self.rubric_repo.get_rubric(db, rubric_id, workspace_id)
            if not r:
                raise ValueError(f"Rubric {rubric_id} not found.")
            rubric = r
        else:
            rubric = self.rubric_service.get_or_create_default_rubric(
                db, suite.organization_id, workspace_id, actor_id
            )

        version = EvaluationSuiteVersion(
            suite_id=suite.id,
            version_number=next_ver_num,
            suite_digest=digest,
            case_count=len(cases),
            rubric_id=rubric.id,
            rubric_version=rubric.version,
            source_dataset_version_id=suite.source_dataset_version_id,
            gate1_approval_id=suite.gate1_approval_id,
            status=SuiteVersionStatus.FINALIZED,
            created_by=actor_id,
        )
        self.suite_repo.create_version(db, version)

        # Associate cases with this version
        for c in cases:
            c.suite_version_id = version.id

        suite.status = EvaluationSuiteStatus.READY
        db.flush()

        logger.info(
            "Finalized EvaluationSuiteVersion %s (v%d, %d cases, digest: %s)",
            version.id,
            version.version_number,
            version.case_count,
            digest[:12],
        )
        return version

    def execute_evaluation_run(
        self,
        db: Session,
        workspace_id: str,
        run_id: str,
        vector_store: VectorStoreProvider,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
    ) -> EvaluationRun:
        """Execute all cases in an evaluation suite version against target and evaluate via rubric."""
        run = self.run_repo.get_run(db, run_id, workspace_id)
        if not run:
            raise ValueError(f"EvaluationRun {run_id} not found in workspace.")

        run.status = EvaluationRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        db.flush()

        # Load suite version
        version = self.suite_repo.get_version(db, run.suite_version_id)
        if not version:
            run.status = EvaluationRunStatus.FAILED
            run.error_message = f"SuiteVersion {run.suite_version_id} not found."
            db.flush()
            return run

        # Load criteria for rubric
        rubric_id = run.rubric_id or version.rubric_id
        criteria = self.rubric_repo.list_criteria(db, rubric_id) if rubric_id else []
        if not criteria:
            default_rubric = self.rubric_service.get_or_create_default_rubric(
                db, run.organization_id, workspace_id, run.created_by
            )
            criteria = self.rubric_repo.list_criteria(db, default_rubric.id)

        # Load cases for this version
        cases = self.case_repo.list_cases_for_suite(db, run.suite_id, suite_version_id=version.id, limit=500)
        run.total_cases = len(cases)

        completed_count = 0
        failed_count = 0
        case_scores: list[float] = []
        metric_sums: dict[str, float] = {}
        metric_counts: dict[str, int] = {}

        supplied_map: dict[str, Any] = {}
        top_k = 4
        score_threshold = 0.0
        system_prompt: str | None = None
        if run.retrieval_config_json:
            try:
                retrieval_conf = json.loads(run.retrieval_config_json)
                supplied_map = retrieval_conf.get("supplied_responses", {})
                if "top_k" in retrieval_conf and retrieval_conf["top_k"] is not None:
                    top_k = int(retrieval_conf["top_k"])
                if "score_threshold" in retrieval_conf and retrieval_conf["score_threshold"] is not None:
                    score_threshold = float(retrieval_conf["score_threshold"])
                if "system_prompt" in retrieval_conf and retrieval_conf["system_prompt"] is not None:
                    system_prompt = str(retrieval_conf["system_prompt"])
            except Exception:
                pass

        for case in cases:
            start_case = time.perf_counter()
            actual_answer = ""
            retrieved_chunks: list[dict[str, Any]] = []
            citations: list[dict[str, Any]] = []

            try:
                # 1. Obtain prediction from Target
                if case.id in supplied_map:
                    supp = supplied_map[case.id]
                    if isinstance(supp, dict):
                        actual_answer = supp.get("answer", "")
                        retrieved_chunks = supp.get("retrieved_chunks", [])
                        citations = supp.get("citations", [])
                    else:
                        actual_answer = str(supp)
                elif run.target_type == EvaluationTargetType.RAG_PIPELINE:
                    rag_res = query_rag(
                        workspace_id=workspace_id,
                        query=case.question,
                        dataset_version_id=version.source_dataset_version_id,
                        vector_store=vector_store,
                        embedding_provider=embedding_provider,
                        llm_provider=llm_provider,
                        top_k=top_k,
                        score_threshold=score_threshold,
                        system_prompt=system_prompt,
                    )
                    actual_answer = rag_res["answer"]
                    retrieved_chunks = rag_res["retrieved_chunks"]
                    citations = rag_res["citations"]
                elif run.target_type == EvaluationTargetType.SUPPLIED_RESPONSES:
                    supp = supplied_map.get(case.id, "")
                    if isinstance(supp, dict):
                        actual_answer = supp.get("answer", "")
                        retrieved_chunks = supp.get("retrieved_chunks", [])
                        citations = supp.get("citations", [])
                    else:
                        actual_answer = str(supp)
                else:
                    llm_res = llm_provider.generate(prompt=case.question)
                    actual_answer = llm_res.text
                    citations = llm_res.citations

                latency = round((time.perf_counter() - start_case) * 1000, 2)
                ans_digest = hashlib.sha256(actual_answer.encode("utf-8")).hexdigest()

                # 2. Persist Case Result
                case_result = EvaluationCaseResult(
                    run_id=run.id,
                    case_id=case.id,
                    actual_answer=actual_answer,
                    actual_answer_digest=ans_digest,
                    overall_case_score=0.0,
                    status="COMPLETED",
                    retrieved_chunks_json=json.dumps(retrieved_chunks),
                    citations_json=json.dumps(citations),
                    latency_ms=latency,
                )
                self.run_repo.add_case_result(db, case_result)

                # 3. Evaluate criteria
                weighted_score_sum = 0.0
                total_weight = 0.0
                metric_results: list[EvaluationMetricResult] = []

                for crit in criteria:
                    evaluator = get_evaluator_by_key(crit.criterion_key) or get_evaluator_by_method(
                        crit.scoring_method
                    )
                    if not evaluator:
                        continue

                    m_result = evaluator.evaluate(
                        query=case.question,
                        expected_answer=case.expected_answer,
                        actual_answer=actual_answer,
                        retrieved_chunks=retrieved_chunks,
                        citations=citations,
                        is_unanswerable=case.is_unanswerable,
                    )

                    metric_db = EvaluationMetricResult(
                        case_result_id=case_result.id,
                        metric_key=crit.criterion_key,
                        raw_score=m_result.raw_score,
                        normalized_score=m_result.normalized_score,
                        score_scale=m_result.score_scale,
                        status=m_result.status,
                        evaluator_version=m_result.evaluator_version,
                        details_json=json.dumps(m_result.details),
                    )
                    metric_results.append(metric_db)

                    # Accumulate weighted score
                    if m_result.status == MetricStatus.MEASURED:
                        weighted_score_sum += m_result.normalized_score * crit.weight
                        total_weight += crit.weight

                        metric_sums[crit.criterion_key] = (
                            metric_sums.get(crit.criterion_key, 0.0) + m_result.normalized_score
                        )
                        metric_counts[crit.criterion_key] = metric_counts.get(crit.criterion_key, 0) + 1

                self.run_repo.add_metric_results_batch(db, metric_results)

                # Overall case score
                case_overall = (weighted_score_sum / total_weight) if total_weight > 0 else 0.0
                case_result.overall_case_score = round(case_overall, 2)
                case_scores.append(case_overall)
                completed_count += 1

            except Exception as exc:
                logger.error("Failed evaluating case %s in run %s: %s", case.id, run.id, exc)
                failed_count += 1

        # 4. Finalize Run Record
        run.completed_cases = completed_count
        run.failed_cases = failed_count
        run.status = EvaluationRunStatus.COMPLETED if failed_count == 0 else EvaluationRunStatus.COMPLETED

        overall_avg = (sum(case_scores) / len(case_scores)) if case_scores else 0.0
        run.overall_score = round(overall_avg, 2)

        breakdown = {
            k: round(metric_sums[k] / metric_counts[k], 2)
            for k in metric_sums
            if metric_counts.get(k, 0) > 0
        }
        run.score_breakdown_json = json.dumps(breakdown)
        run.completed_at = datetime.now(UTC)
        db.flush()

        logger.info(
            "Completed EvaluationRun %s: score %.2f%% (%d/%d passed)",
            run.id,
            run.overall_score,
            completed_count,
            run.total_cases,
        )
        return run
