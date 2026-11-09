"""Deterministic Mock Examination Generator for offline unit testing."""

from __future__ import annotations

from typing import Any

from app.models.evaluation import CaseCategory, DifficultyLevel
from app.modules.evaluation.generators.base import (
    ExamGenerator,
    GeneratedCaseCandidate,
)


class MockExamGenerator(ExamGenerator):
    """Deterministic generator producing predefined examination candidates."""

    def generate_candidates(
        self,
        masked_documents: list[dict[str, Any]],
        target_count: int = 10,
        language: str = "en",
        categories: list[CaseCategory] | None = None,
        difficulty_distribution: dict[DifficultyLevel, float] | None = None,
        include_unanswerable: bool = True,
        **kwargs: Any,
    ) -> list[GeneratedCaseCandidate]:
        first_doc_id = masked_documents[0].get("document_id", "doc-mock-1") if masked_documents else "doc-mock-1"

        candidates = [
            GeneratedCaseCandidate(
                question="What is the corporate budget approval threshold exceeding 50,000 AED?",
                expected_answer="All corporate budget approvals exceeding 50,000 AED require Senior Executive sign-off.",
                category=CaseCategory.NUMERICAL,
                difficulty=DifficultyLevel.HARD,
                language=language,
                is_unanswerable=False,
                source_document_id=first_doc_id,
                source_offset_start=0,
                source_offset_end=95,
                evidence_text="All corporate budget approvals exceeding 50,000 AED require Senior Executive sign-off.",
            ),
            GeneratedCaseCandidate(
                question="What KYC standards must customer accounts comply with?",
                expected_answer="Customer accounts must comply with Central Bank regulatory compliance and KYC standards.",
                category=CaseCategory.PROCEDURAL,
                difficulty=DifficultyLevel.MEDIUM,
                language=language,
                is_unanswerable=False,
                source_document_id=first_doc_id,
                source_offset_start=96,
                source_offset_end=185,
                evidence_text="Customer accounts must comply with Central Bank regulatory compliance and KYC standards.",
            ),
            GeneratedCaseCandidate(
                question="What is the policy on corporate funding for deep-sea mining expeditions?",
                expected_answer="The documentation does not contain any policy regarding deep-sea mining expeditions.",
                category=CaseCategory.UNANSWERABLE,
                difficulty=DifficultyLevel.HARD,
                language=language,
                is_unanswerable=True,
                source_document_id=first_doc_id,
                source_offset_start=0,
                source_offset_end=0,
                evidence_text="",
            ),
        ]
        return candidates[:target_count]
