"""Unit tests for Evaluation Question Generators and Split Logic."""

from __future__ import annotations

from app.models.evaluation import CaseCategory, DifficultyLevel, SplitType
from app.modules.evaluation.generators.mock_generator import MockExamGenerator
from app.modules.evaluation.generators.rule_based_generator import (
    RuleBasedExamGenerator,
    compute_split,
)


def test_deterministic_split_assignment():
    """Verify compute_split assigns stable, reproducible splits based on suite_id and question."""
    split1 = compute_split("suite-123", "What is corporate policy?")
    split2 = compute_split("suite-123", "What is corporate policy?")
    assert split1 == split2
    assert split1 in (SplitType.DEVELOPMENT, SplitType.VALIDATION, SplitType.HOLDOUT)

    # Different question should hash independently
    split3 = compute_split("suite-123", "Another completely different question?")
    assert split3 in (SplitType.DEVELOPMENT, SplitType.VALIDATION, SplitType.HOLDOUT)


def test_rule_based_generator_categories_and_offsets():
    """Verify RuleBasedExamGenerator extracts categorized questions with accurate source offsets."""
    generator = RuleBasedExamGenerator()

    sample_text = (
        "Mizan Financial Guidelines and Compliance Standards.\n"
        "All corporate budget approvals exceeding 50,000 AED require Senior Executive sign-off.\n"
        "Customer accounts must comply with Central Bank regulatory compliance and KYC standards.\n"
        "Risk management procedures are defined as the systematic identification of vulnerabilities."
    )

    masked_docs = [
        {
            "document_id": "doc-policy-01",
            "document_name": "policies.txt",
            "text": sample_text,
        }
    ]

    candidates = generator.generate_candidates(
        masked_documents=masked_docs,
        target_count=5,
        language="en",
        include_unanswerable=True,
    )

    assert len(candidates) >= 3

    # Check categories
    categories = {c.category for c in candidates}
    assert CaseCategory.NUMERICAL in categories or CaseCategory.PROCEDURAL in categories
    assert CaseCategory.UNANSWERABLE in categories

    # Verify numerical candidate
    num_cand = next((c for c in candidates if c.category == CaseCategory.NUMERICAL), None)
    if num_cand:
        assert "threshold" in num_cand.question.lower() or "limit" in num_cand.question.lower()
        assert "50,000 AED" in num_cand.expected_answer
        assert num_cand.source_document_id == "doc-policy-01"
        assert num_cand.source_offset_start >= 0
        assert num_cand.source_offset_end > num_cand.source_offset_start
        assert num_cand.difficulty in (DifficultyLevel.MEDIUM, DifficultyLevel.HARD)

    # Verify unanswerable candidate
    unans_cand = next((c for c in candidates if c.category == CaseCategory.UNANSWERABLE), None)
    assert unans_cand is not None
    assert unans_cand.is_unanswerable is True
    assert "does not contain" in unans_cand.expected_answer.lower() or "not mention" in unans_cand.expected_answer.lower()


def test_mock_exam_generator():
    """Verify MockExamGenerator produces deterministic candidates."""
    mock_gen = MockExamGenerator()
    candidates = mock_gen.generate_candidates(masked_documents=[], target_count=3)
    assert len(candidates) == 3
    assert candidates[0].category == CaseCategory.NUMERICAL
    assert candidates[1].category == CaseCategory.PROCEDURAL
    assert candidates[2].category == CaseCategory.UNANSWERABLE
    assert candidates[2].is_unanswerable is True
