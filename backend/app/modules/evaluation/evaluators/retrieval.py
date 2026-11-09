"""Retrieval Quality Evaluator (Precision@K, Recall@K, MRR)."""

from __future__ import annotations

from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


class RetrievalEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "retrieval_quality"

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
        config = configuration or {}
        gold_doc_ids = set(config.get("gold_document_ids", []))
        top_k = config.get("top_k", len(chunks))

        if not chunks:
            # If query is unanswerable, retrieving no chunks is acceptable
            score = 100.0 if is_unanswerable else 0.0
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=1.0 if is_unanswerable else 0.0,
                normalized_score=score,
                status=MetricStatus.MEASURED,
                evaluator_version=self.version,
                details={"message": "No chunks retrieved."},
            )

        # Measure Recall & Precision against gold doc IDs if provided
        if gold_doc_ids:
            retrieved_doc_ids = [c.get("document_id") for c in chunks[:top_k]]
            relevant_retrieved = sum(1 for did in retrieved_doc_ids if did in gold_doc_ids)

            precision = relevant_retrieved / max(1, len(retrieved_doc_ids))
            recall = relevant_retrieved / max(1, len(gold_doc_ids))

            # MRR (first relevant rank)
            mrr = 0.0
            for rank, did in enumerate(retrieved_doc_ids, start=1):
                if did in gold_doc_ids:
                    mrr = 1.0 / rank
                    break

            composite = 0.4 * precision + 0.4 * recall + 0.2 * mrr
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=round(composite, 4),
                normalized_score=round(composite * 100.0, 2),
                status=MetricStatus.MEASURED,
                evaluator_version=self.version,
                details={
                    "precision_at_k": round(precision, 4),
                    "recall_at_k": round(recall, 4),
                    "mrr": round(mrr, 4),
                },
            )

        # Fallback: heuristic query-word overlap in chunks
        query_words = set(query.lower().split())
        relevant_chunks = 0
        for c in chunks[:top_k]:
            c_text = c.get("text", "").lower()
            if any(qw in c_text for qw in query_words if len(qw) > 3):
                relevant_chunks += 1

        precision = relevant_chunks / max(1, len(chunks[:top_k]))
        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=round(precision, 4),
            normalized_score=round(precision * 100.0, 2),
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "heuristic_relevant_chunks": relevant_chunks,
                "total_chunks": len(chunks[:top_k]),
            },
        )
