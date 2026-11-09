"""Central Registry for Metric Evaluators."""

from __future__ import annotations

from app.models.evaluation import ScoringMethod
from app.modules.evaluation.evaluators.abstention import AbstentionEvaluator
from app.modules.evaluation.evaluators.base import MetricEvaluator
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

_EVALUATORS: dict[str, MetricEvaluator] = {
    "exact_match": ExactMatchEvaluator(),
    "token_f1": TokenF1Evaluator(),
    "keyword_coverage": KeywordCoverageEvaluator(),
    "retrieval_quality": RetrievalEvaluator(),
    "context_relevance": ContextRelevanceEvaluator(),
    "faithfulness": FaithfulnessEvaluator(),
    "groundedness": GroundednessEvaluator(),
    "citation_verification": CitationEvaluator(),
    "appropriate_abstention": AbstentionEvaluator(),
    "safety": SafetyEvaluator(),
    "compliance": ComplianceEvaluator(),
}

_SCORING_METHOD_MAP: dict[ScoringMethod, str] = {
    ScoringMethod.EXACT_MATCH: "exact_match",
    ScoringMethod.TOKEN_F1: "token_f1",
    ScoringMethod.KEYWORD_COVERAGE: "keyword_coverage",
    ScoringMethod.RETRIEVAL_METRIC: "retrieval_quality",
    ScoringMethod.CONTEXT_RELEVANCE: "context_relevance",
    ScoringMethod.FAITHFULNESS: "faithfulness",
    ScoringMethod.GROUNDEDNESS: "groundedness",
    ScoringMethod.CITATION_VERIFICATION: "citation_verification",
    ScoringMethod.ABSTENTION: "appropriate_abstention",
    ScoringMethod.SAFETY: "safety",
    ScoringMethod.COMPLIANCE: "compliance",
}


def get_evaluator_by_key(metric_key: str) -> MetricEvaluator | None:
    return _EVALUATORS.get(metric_key.lower())


def get_evaluator_by_method(method: ScoringMethod) -> MetricEvaluator | None:
    key = _SCORING_METHOD_MAP.get(method)
    return _EVALUATORS.get(key) if key else None


def list_registered_evaluators() -> list[str]:
    return list(_EVALUATORS.keys())
