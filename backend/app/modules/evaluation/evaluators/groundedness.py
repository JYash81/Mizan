"""Groundedness Evaluator measuring presence and attribution to approved business sources."""

from __future__ import annotations

import re
from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


class GroundednessEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "groundedness"

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
        citations_list = citations or []

        # If question is unanswerable and actual answer acknowledges abstention
        if is_unanswerable:
            abstention_phrases = [
                "not contain", "unmentioned", "does not state", "do not state", "not stated",
                "not authorized", "no information", "not provided", "do not have", "does not have",
                "not available", "not found"
            ]
            if any(p in actual_answer.lower() for p in abstention_phrases):
                return MetricScoreResult(
                    metric_key=self.metric_key,
                    raw_score=1.0,
                    normalized_score=100.0,
                    status=MetricStatus.MEASURED,
                    evaluator_version=self.version,
                    details={"grounded_abstention": True},
                )

        if not chunks:
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=0.0,
                normalized_score=0.0,
                status=MetricStatus.MEASURED,
                evaluator_version=self.version,
                details={"message": "No source context available to ground the response."},
            )

        # 1. Check citation presence in answer
        citation_matches = re.findall(r"\[Doc:\s*([A-Za-z0-9_\-]+),\s*Chunk:\s*(\d+)\]", actual_answer)
        has_citations = len(citation_matches) > 0 or len(citations_list) > 0

        # 2. Check token grounding in retrieved chunks
        stopwords = {
            "a", "an", "the", "and", "or", "but", "if", "because", "as", "what", "which",
            "this", "that", "these", "those", "then", "just", "so", "than", "such", "both",
            "through", "during", "before", "after", "above", "below", "to", "from", "up",
            "down", "in", "out", "on", "off", "over", "under", "again", "further", "then",
            "once", "here", "there", "when", "where", "why", "how", "all", "any", "both",
            "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "too", "very", "can", "will", "should", "now",
            "according", "states", "stated", "state", "based", "chunk", "doc", "document",
            "source", "reference", "policy"
        }

        # Remove explicit citation tags before lexical comparison
        clean_answer = re.sub(r"\[Doc:\s*[^\]]+\]", " ", actual_answer, flags=re.IGNORECASE)
        context_words = set(re.findall(r"\w+", " ".join(c.get("text", "") for c in chunks).lower()))
        answer_words = [w for w in re.findall(r"\w+", clean_answer.lower()) if len(w) > 2 and w not in stopwords]

        if not answer_words:
            overlap_ratio = 1.0
        else:
            grounded_words = sum(1 for w in answer_words if w in context_words)
            overlap_ratio = grounded_words / len(answer_words)

        # Combined groundedness score (60% lexical grounding + 40% citation attribution)
        citation_factor = 1.0 if has_citations else 0.5
        composite = 0.6 * overlap_ratio + 0.4 * citation_factor

        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=round(composite, 4),
            normalized_score=round(composite * 100.0, 2),
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "overlap_ratio": round(overlap_ratio, 4),
                "has_citations": has_citations,
                "citation_count": len(citation_matches) or len(citations_list),
            },
        )
