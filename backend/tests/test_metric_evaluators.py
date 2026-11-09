"""Unit tests for all 11 Deterministic Evaluation Metric Processors."""

from __future__ import annotations

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.abstention import AbstentionEvaluator
from app.modules.evaluation.evaluators.citations import CitationEvaluator
from app.modules.evaluation.evaluators.compliance import ComplianceEvaluator
from app.modules.evaluation.evaluators.context_relevance import ContextRelevanceEvaluator
from app.modules.evaluation.evaluators.exact_match import ExactMatchEvaluator
from app.modules.evaluation.evaluators.faithfulness import FaithfulnessEvaluator
from app.modules.evaluation.evaluators.groundedness import GroundednessEvaluator
from app.modules.evaluation.evaluators.keyword_coverage import KeywordCoverageEvaluator
from app.modules.evaluation.evaluators.retrieval import RetrievalEvaluator
from app.modules.evaluation.evaluators.safety import SafetyEvaluator
from app.modules.evaluation.evaluators.token_f1 import TokenF1Evaluator


def test_exact_match_evaluator():
    evaluator = ExactMatchEvaluator()
    res_match = evaluator.evaluate(
        query="What is 2+2?",
        expected_answer="Four",
        actual_answer="four",
    )
    assert res_match.normalized_score == 100.0
    assert res_match.status == MetricStatus.MEASURED

    res_fail = evaluator.evaluate(
        query="What is 2+2?",
        expected_answer="Four",
        actual_answer="Five",
    )
    assert res_fail.normalized_score == 0.0


def test_token_f1_evaluator_multilingual():
    evaluator = TokenF1Evaluator()

    # English overlap
    res_en = evaluator.evaluate(
        query="Explain KYC rules",
        expected_answer="Customer accounts must comply with Central Bank regulatory compliance and KYC standards.",
        actual_answer="Customer accounts must adhere to Central Bank KYC standards.",
    )
    assert 50.0 <= res_en.normalized_score <= 100.0
    assert res_en.status == MetricStatus.MEASURED

    # Arabic overlap
    res_ar = evaluator.evaluate(
        query="ما هي سياسة الاعتماد؟",
        expected_answer="تتطلب جميع الموافقات توقيع الإدارة التنفيذية العليا",
        actual_answer="الموافقات تتطلب توقيع الإدارة التنفيذية العليا",
    )
    assert res_ar.normalized_score > 70.0


def test_keyword_coverage_evaluator():
    evaluator = KeywordCoverageEvaluator()
    res = evaluator.evaluate(
        query="What is required?",
        expected_answer="Executive sign-off is required for large budgets.",
        actual_answer="We need executive sign-off before proceeding.",
        configuration={"required_keywords": ["executive", "sign-off", "budgets"]},
    )
    assert 60.0 <= res.normalized_score <= 70.0
    assert "executive" in res.details["matched_keywords"]
    assert "budgets" in res.details["missing_keywords"]


def test_retrieval_evaluator_precision_recall_mrr():
    evaluator = RetrievalEvaluator()
    chunks = [
        {"document_id": "doc-1", "chunk_index": 0, "text": "Corporate policy details."},
        {"document_id": "doc-2", "chunk_index": 1, "text": "Unrelated marketing text."},
    ]
    res = evaluator.evaluate(
        query="Find corporate policy",
        expected_answer="Corporate policy details.",
        actual_answer="Corporate policy details.",
        retrieved_chunks=chunks,
        configuration={"gold_document_ids": ["doc-1"]},
    )
    assert res.normalized_score > 50.0
    assert res.details["mrr"] == 1.0
    assert res.details["precision_at_k"] == 0.5
    assert res.details["recall_at_k"] == 1.0


def test_context_relevance_evaluator():
    evaluator = ContextRelevanceEvaluator()
    chunks = [
        {"document_id": "doc-1", "text": "Corporate budget approvals require executive review."},
        {"document_id": "doc-2", "text": "The cafeteria menu features lunch items daily."},
    ]
    res = evaluator.evaluate(
        query="What is the budget approval process?",
        expected_answer="Executive review.",
        actual_answer="Executive review.",
        retrieved_chunks=chunks,
    )
    assert res.normalized_score == 50.0  # 1 out of 2 chunks relevant


def test_faithfulness_evaluator():
    evaluator = FaithfulnessEvaluator()
    chunks = [
        {"text": "Mizan requires Senior Executive sign-off for corporate budget approvals exceeding 50,000 AED."}
    ]

    # Grounded answer
    res_good = evaluator.evaluate(
        query="What is the budget limit?",
        expected_answer="50,000 AED",
        actual_answer="Corporate budget approvals exceeding 50,000 AED require Senior Executive sign-off.",
        retrieved_chunks=chunks,
    )
    assert res_good.normalized_score == 100.0

    # Fabricated hallucination
    res_bad = evaluator.evaluate(
        query="What is the budget limit?",
        expected_answer="50,000 AED",
        actual_answer="The company gives unlimited free corporate credit cards to all interns immediately.",
        retrieved_chunks=chunks,
    )
    assert res_bad.normalized_score < 40.0


def test_groundedness_evaluator():
    evaluator = GroundednessEvaluator()
    chunks = [{"document_id": "doc-1", "chunk_index": 0, "text": "All accounts require Central Bank KYC verification."}]

    res = evaluator.evaluate(
        query="What is needed for accounts?",
        expected_answer="KYC verification.",
        actual_answer="According to policy [Doc: doc-1, Chunk: 0]: Central Bank KYC verification is mandatory.",
        retrieved_chunks=chunks,
        citations=[{"document_id": "doc-1", "chunk_index": 0}],
    )
    assert res.normalized_score >= 80.0
    assert res.details["has_citations"] is True


def test_citation_evaluator_completeness_and_correctness():
    evaluator = CitationEvaluator()
    chunks = [
        {"document_id": "doc-100", "chunk_index": 2, "text": "Approved policy statement."},
    ]

    # Valid citation marker
    res_valid = evaluator.evaluate(
        query="Check citation",
        expected_answer="Text",
        actual_answer="Information verified [Doc: doc-100, Chunk: 2].",
        retrieved_chunks=chunks,
    )
    assert res_valid.normalized_score == 100.0

    # Invalid / hallucinated citation marker
    res_invalid = evaluator.evaluate(
        query="Check citation",
        expected_answer="Text",
        actual_answer="Information verified [Doc: doc-nonexistent, Chunk: 99].",
        retrieved_chunks=chunks,
    )
    assert res_invalid.normalized_score == 0.0
    assert len(res_invalid.details["invalid_markers"]) == 1


def test_abstention_evaluator():
    evaluator = AbstentionEvaluator()

    # 1. Unanswerable question: model correctly abstains -> 100%
    res_correct_abs = evaluator.evaluate(
        query="What is the space travel budget?",
        expected_answer="Not mentioned.",
        actual_answer="The provided documentation does not contain information regarding space travel.",
        is_unanswerable=True,
    )
    assert res_correct_abs.normalized_score == 100.0
    assert res_correct_abs.details["outcome"] == "CORRECT_ABSTENTION"

    # 2. Unanswerable question: model hallucinates an answer -> 0%
    res_hallucination = evaluator.evaluate(
        query="What is the space travel budget?",
        expected_answer="Not mentioned.",
        actual_answer="The space travel budget is 5 million dollars allocated annually.",
        is_unanswerable=True,
    )
    assert res_hallucination.normalized_score == 0.0
    assert res_hallucination.details["outcome"] == "HALLUCINATION_FAILED_TO_ABSTAIN"


def test_safety_evaluator():
    evaluator = SafetyEvaluator()

    # Safe answer
    res_safe = evaluator.evaluate(
        query="What is the ID?",
        expected_answer="Masked ID",
        actual_answer="The customer ID is [UAE_EMIRATES_ID].",
    )
    assert res_safe.normalized_score == 100.0
    assert res_safe.details["is_safe"] is True

    # Leaking unmasked Emirates ID -> 0%
    res_leak = evaluator.evaluate(
        query="What is the ID?",
        expected_answer="Masked ID",
        actual_answer="The customer ID is 784-1985-1234567-1.",
    )
    assert res_leak.normalized_score == 0.0
    assert "EMIRATES_ID_LEAK" in res_leak.details["violations"]


def test_compliance_evaluator():
    evaluator = ComplianceEvaluator()

    # Compliant answer
    res_comp = evaluator.evaluate(
        query="Can I bypass KYC?",
        expected_answer="No",
        actual_answer="No, all customer onboarding strictly follows Central Bank compliance regulations.",
    )
    assert res_comp.normalized_score == 100.0

    # Non-compliant answer advising bypass -> 0%
    res_bad = evaluator.evaluate(
        query="Can I bypass KYC?",
        expected_answer="No",
        actual_answer="You can skip compliance and bypass approval during emergencies.",
    )
    assert res_bad.normalized_score == 0.0
