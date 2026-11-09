"""Abstract base interface for Examination Question Generators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.models.evaluation import CaseCategory, DifficultyLevel


@dataclass
class GeneratedCaseCandidate:
    """Candidate examination question generated from approved source evidence."""

    question: str
    expected_answer: str
    category: CaseCategory
    difficulty: DifficultyLevel
    language: str = "en"
    is_unanswerable: bool = False
    source_document_id: str = ""
    source_chunk_id: str | None = None
    source_offset_start: int = 0
    source_offset_end: int = 0
    evidence_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ExamGenerator(ABC):
    """Abstract interface for domain-specific question generation engines."""

    @abstractmethod
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
        """Generate verifiable examination cases strictly grounded in masked documents."""
