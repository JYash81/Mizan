"""Exam Generation Service with strict Gate 1 human approval enforcement."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import DatasetVersion, Document
from app.models.evaluation import (
    EvaluationCase,
    EvaluationSuiteStatus,
    GroundTruthStatus,
)
from app.modules.evaluation.generators.base import ExamGenerator
from app.modules.evaluation.generators.mock_generator import MockExamGenerator
from app.modules.evaluation.generators.rule_based_generator import (
    RuleBasedExamGenerator,
    compute_split,
)
from app.modules.evaluation.repositories.case_repository import CaseRepository
from app.modules.evaluation.repositories.suite_repository import SuiteRepository
from app.modules.masking.approval.gate1_service import require_gate1_approval
from app.modules.storage import StorageBucket, StorageProvider

logger = logging.getLogger(__name__)


class ExamGenerationService:
    def __init__(
        self,
        suite_repo: SuiteRepository | None = None,
        case_repo: CaseRepository | None = None,
    ):
        self.suite_repo = suite_repo or SuiteRepository()
        self.case_repo = case_repo or CaseRepository()

    def generate_suite_cases(
        self,
        db: Session,
        workspace_id: str,
        suite_id: str,
        dataset_version_id: str,
        actor_id: str,
        storage: StorageProvider,
        target_question_count: int = 10,
        language: str = "en",
        generation_method: str = "rule_based",
        include_unanswerable: bool = True,
    ) -> list[EvaluationCase]:
        """Generate verifiable examination cases strictly grounded in Gate 1 approved masked documents.

        FAIL-CLOSED INVARIANT: Enforces require_gate1_approval() before processing any documents.
        """
        suite = self.suite_repo.get_suite(db, workspace_id, suite_id)
        if not suite:
            raise ValueError(f"EvaluationSuite {suite_id} not found in workspace.")

        # 1. Gate 1 Human Approval Check (Fails closed with HTTP 403 if unapproved)
        approval = require_gate1_approval(
            db=db,
            workspace_id=workspace_id,
            dataset_version_id=dataset_version_id,
            storage=storage,
        )

        version = db.execute(
            select(DatasetVersion).where(DatasetVersion.id == dataset_version_id)
        ).scalar_one_or_none()
        if not version:
            raise ValueError(f"DatasetVersion {dataset_version_id} not found.")

        # 2. Load approved masked text from StorageBucket.MASKED_DATASETS
        documents = (
            db.execute(select(Document).where(Document.dataset_version_id == version.id))
            .scalars()
            .all()
        )

        masked_docs: list[dict[str, Any]] = []
        for doc in documents:
            masked_key = f"runs/{approval.masking_run_id}/docs/{doc.id}.masked.txt"
            try:
                data, _ = storage.get_object(StorageBucket.MASKED_DATASETS, masked_key)
                text = data.decode("utf-8", errors="replace")
                if text.strip():
                    masked_docs.append(
                        {
                            "document_id": doc.id,
                            "document_name": doc.name,
                            "text": text,
                        }
                    )
            except Exception as exc:
                logger.warning("Could not read masked document %s at %s: %s", doc.id, masked_key, exc)

        if not masked_docs:
            raise ValueError(
                f"No masked document content found in StorageBucket.MASKED_DATASETS for approval {approval.id}."
            )

        # 3. Select Generator Engine
        generator: ExamGenerator
        if generation_method == "mock":
            generator = MockExamGenerator()
        else:
            generator = RuleBasedExamGenerator()

        # 4. Generate Candidates
        candidates = generator.generate_candidates(
            masked_documents=masked_docs,
            target_count=target_question_count,
            language=language,
            include_unanswerable=include_unanswerable,
        )

        # 5. Persist EvaluationCases
        created_cases: list[EvaluationCase] = []
        for cand in candidates:
            split = compute_split(suite.id, cand.question)
            case = EvaluationCase(
                organization_id=suite.organization_id,
                workspace_id=suite.workspace_id,
                suite_id=suite.id,
                case_type="standard",
                category=cand.category,
                difficulty=cand.difficulty,
                split=split,
                language=cand.language,
                question=cand.question,
                expected_answer=cand.expected_answer,
                is_unanswerable=cand.is_unanswerable,
                source_document_ids_json=json.dumps([cand.source_document_id] if cand.source_document_id else []),
                source_chunk_ids_json=json.dumps([cand.source_chunk_id] if cand.source_chunk_id else []),
                source_offsets_json=json.dumps(
                    [{"start": cand.source_offset_start, "end": cand.source_offset_end}]
                    if cand.source_offset_end > 0
                    else []
                ),
                ground_truth_status=GroundTruthStatus.GENERATED,
                generation_method=generation_method,
                created_by=actor_id,
            )
            created_cases.append(case)

        self.case_repo.create_cases_batch(db, created_cases)

        # 6. Update Suite Metadata
        suite.source_dataset_id = version.dataset_id
        suite.source_dataset_version_id = version.id
        suite.gate1_approval_id = approval.id
        suite.status = EvaluationSuiteStatus.REVIEW_REQUIRED
        suite.generation_method = generation_method
        db.flush()

        logger.info(
            "Generated %d evaluation cases for suite %s (Gate 1 approval %s)",
            len(created_cases),
            suite.id,
            approval.id,
        )
        return created_cases
