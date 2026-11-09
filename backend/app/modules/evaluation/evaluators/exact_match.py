"""Exact Match metric evaluator with normalized comparison."""

from __future__ import annotations

import re
from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, stripping punctuation, and compressing whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


class ExactMatchEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "exact_match"

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
        if is_unanswerable:
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=1.0,
                normalized_score=100.0,
                status=MetricStatus.NOT_APPLICABLE,
                evaluator_version=self.version,
                details={"message": "Exact match not applicable for unanswerable questions."},
            )

        norm_expected = normalize_text(expected_answer)
        norm_actual = normalize_text(actual_answer)

        is_match = norm_expected == norm_actual or (norm_expected in norm_actual and len(norm_expected) > 10)
        score = 100.0 if is_match else 0.0

        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=1.0 if is_match else 0.0,
            normalized_score=score,
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "is_match": is_match,
                "norm_expected_length": len(norm_expected),
                "norm_actual_length": len(norm_actual),
            },
        )
