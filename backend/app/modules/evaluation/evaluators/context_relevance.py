"""Context Relevance evaluator measuring signal-to-noise ratio of retrieved passages."""

from __future__ import annotations

import re
from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


class ContextRelevanceEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "context_relevance"

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
        chunks = retrieved_chunks or []
        if not chunks:
            score = 100.0 if is_unanswerable else 0.0
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=1.0 if is_unanswerable else 0.0,
                normalized_score=score,
                status=MetricStatus.MEASURED,
                evaluator_version=self.version,
                details={"message": "No context chunks retrieved."},
            )

        query_tokens = set(re.findall(r"\w+", query.lower()))
        informative_tokens = {t for t in query_tokens if len(t) > 3}

        if not informative_tokens:
            informative_tokens = query_tokens

        matching_chunks = 0
        chunk_scores: list[float] = []

        for c in chunks:
            c_text = c.get("text", "").lower()
            overlap = sum(1 for t in informative_tokens if t in c_text)
            c_ratio = overlap / max(1, len(informative_tokens))
            chunk_scores.append(round(c_ratio, 4))
            if c_ratio > 0.2:
                matching_chunks += 1

        relevance_ratio = matching_chunks / len(chunks)

        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=round(relevance_ratio, 4),
            normalized_score=round(relevance_ratio * 100.0, 2),
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "matching_chunks": matching_chunks,
                "total_chunks": len(chunks),
                "chunk_scores": chunk_scores,
            },
        )
