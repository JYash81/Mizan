"""Citation Completeness and Correctness Evaluator."""

from __future__ import annotations

import re
from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


class CitationEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "citation_verification"

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

        # If question is unanswerable, citations are not required
        if is_unanswerable:
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=1.0,
                normalized_score=100.0,
                status=MetricStatus.NOT_APPLICABLE,
                evaluator_version=self.version,
                details={"message": "Unanswerable query; citations not expected."},
            )

        # 1. Parse inline citation markers: [Doc: <id>, Chunk: <index>]
        inline_markers = re.findall(r"\[Doc:\s*([A-Za-z0-9_\-]+),\s*Chunk:\s*(\d+)\]", actual_answer)

        # Map valid chunks from retrieved context: (doc_id, chunk_index)
        valid_chunks_map: set[tuple[str, int]] = set()
        for c in chunks:
            doc_id = str(c.get("document_id", "")).strip()
            chunk_idx = int(c.get("chunk_index", 0))
            valid_chunks_map.add((doc_id, chunk_idx))

        total_citations = len(inline_markers)
        if total_citations == 0:
            if citations_list:
                # Citations returned in payload rather than inline
                total_citations = len(citations_list)
                valid_count = 0
                for cit in citations_list:
                    doc_id = str(cit.get("document_id", "")).strip()
                    c_idx = int(cit.get("chunk_index", 0))
                    if (doc_id, c_idx) in valid_chunks_map or any(doc_id in k[0] for k in valid_chunks_map):
                        valid_count += 1
                ratio = valid_count / total_citations
                return MetricScoreResult(
                    metric_key=self.metric_key,
                    raw_score=round(ratio, 4),
                    normalized_score=round(ratio * 100.0, 2),
                    status=MetricStatus.MEASURED,
                    evaluator_version=self.version,
                    details={
                        "total_citations": total_citations,
                        "valid_citations": valid_count,
                        "format": "payload",
                    },
                )
            else:
                return MetricScoreResult(
                    metric_key=self.metric_key,
                    raw_score=0.0,
                    normalized_score=0.0,
                    status=MetricStatus.MEASURED,
                    evaluator_version=self.version,
                    details={"message": "No inline citation markers found in answer text."},
                )

        # Validate inline markers against retrieved chunks
        valid_inline = 0
        invalid_markers: list[str] = []

        for doc_id, chunk_str in inline_markers:
            chunk_idx = int(chunk_str)
            # Accept match on full ID or prefix match
            if (doc_id, chunk_idx) in valid_chunks_map or any(doc_id in k[0] for k in valid_chunks_map):
                valid_inline += 1
            else:
                invalid_markers.append(f"[Doc: {doc_id}, Chunk: {chunk_idx}]")

        correctness_ratio = valid_inline / total_citations

        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=round(correctness_ratio, 4),
            normalized_score=round(correctness_ratio * 100.0, 2),
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "total_inline_citations": total_citations,
                "valid_inline_citations": valid_inline,
                "invalid_markers": invalid_markers,
            },
        )
