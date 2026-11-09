"""Appropriate Abstention Evaluator measuring hallucination avoidance on unanswerable queries."""

from __future__ import annotations

import re
from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult

ABSTENTION_INDICATORS = [
    r"\bdoes not contain\b",
    r"\bdo not contain\b",
    r"\bno information\b",
    r"\bnot mentioned\b",
    r"\bnot authorized\b",
    r"\bunmentioned\b",
    r"\bcannot answer\b",
    r"\bnot provided\b",
    r"\binsufficient evidence\b",
    r"\bunavailable\b",
    r"\bno matching\b",
    r"\bno records\b",
    r"\bdo not state\b",
    r"\bdoes not state\b",
    r"\bnot state\b",
    r"\bnot stated\b",
    r"\bdo not have\b",
    r"\bdoes not have\b",
    r"\bnot available\b",
    r"\bnot found\b",
    r"\bnot covered\b",
    r"\bnot specified\b",
    r"\bnot disclose\b",
]


def detects_abstention(text: str) -> bool:
    lower_text = text.lower()
    return any(re.search(pattern, lower_text) for pattern in ABSTENTION_INDICATORS)


class AbstentionEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "appropriate_abstention"

    def evaluate(
        self,
        query: str,
        expected_answer: str,
        actual_answer: str,
        retrieved_chunks: list[dict[str, Any]] | None = None,
        citations: list[dict[str, Any]] | None = None,
        is_unanswerable: bool = False,
        configuration: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MetricScoreResult:
        actual_abstains = detects_abstention(actual_answer)

        if is_unanswerable:
            # Query is unanswerable: model SHOULD abstain
            if actual_abstains:
                return MetricScoreResult(
                    metric_key=self.metric_key,
                    raw_score=1.0,
                    normalized_score=100.0,
                    status=MetricStatus.MEASURED,
                    evaluator_version=self.version,
                    details={"outcome": "CORRECT_ABSTENTION", "is_unanswerable": True},
                )
            else:
                # Hallucination / failure to abstain
                return MetricScoreResult(
                    metric_key=self.metric_key,
                    raw_score=0.0,
                    normalized_score=0.0,
                    status=MetricStatus.MEASURED,
                    evaluator_version=self.version,
                    details={
                        "outcome": "HALLUCINATION_FAILED_TO_ABSTAIN",
                        "is_unanswerable": True,
                        "message": "Model generated answer for an unanswerable query unsupported by documentation.",
                    },
                )
        else:
            # Query is answerable: model should NOT abstain unless context was empty
            chunks = retrieved_chunks or []
            if actual_abstains and len(chunks) > 0:
                # False abstention
                return MetricScoreResult(
                    metric_key=self.metric_key,
                    raw_score=0.2,
                    normalized_score=20.0,
                    status=MetricStatus.MEASURED,
                    evaluator_version=self.version,
                    details={"outcome": "FALSE_ABSTENTION", "is_unanswerable": False},
                )
            else:
                return MetricScoreResult(
                    metric_key=self.metric_key,
                    raw_score=1.0,
                    normalized_score=100.0,
                    status=MetricStatus.MEASURED,
                    evaluator_version=self.version,
                    details={"outcome": "APPROPRIATE_ANSWER", "is_unanswerable": False},
                )
