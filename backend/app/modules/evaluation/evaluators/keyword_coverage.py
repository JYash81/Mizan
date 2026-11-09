"""Keyword Coverage evaluator measuring presence of critical domain terminology."""

from __future__ import annotations

import re
from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


class KeywordCoverageEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "keyword_coverage"

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
        config = configuration or {}
        # Explicit required keywords or extracted content words from expected_answer (>3 chars)
        required_keywords = config.get("required_keywords")
        if not required_keywords:
            stopwords = {"the", "and", "for", "with", "this", "that", "from", "are", "was", "were", "what", "which"}
            all_words = re.findall(r"\b[A-Za-z0-9_\u0600-\u06FF]{4,}\b", expected_answer.lower())
            required_keywords = [w for w in all_words if w not in stopwords]

        if not required_keywords:
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=1.0,
                normalized_score=100.0,
                status=MetricStatus.NOT_APPLICABLE,
                evaluator_version=self.version,
                details={"message": "No keywords specified or extracted."},
            )

        actual_lower = actual_answer.lower()
        matched = [kw for kw in required_keywords if kw.lower() in actual_lower]
        ratio = len(matched) / len(required_keywords)

        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=round(ratio, 4),
            normalized_score=round(ratio * 100.0, 2),
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "total_keywords": len(required_keywords),
                "matched_keywords": matched,
                "missing_keywords": [kw for kw in required_keywords if kw not in matched],
            },
        )
