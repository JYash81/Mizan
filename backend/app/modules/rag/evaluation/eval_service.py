"""Deterministic, offline RAG Evaluation Engine for Mizan.

Evaluates:
1. Context Relevance: Fraction of retrieved context relevant to query.
2. Retrieval Recall: Fraction of gold reference keywords/documents retrieved.
3. Faithfulness: Degree to which the answer is grounded in the retrieved chunks.
4. Citation Completeness: Presence and validity of verifiable source markers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class RAGEvaluationReport:
    """Detailed quantitative evaluation metrics for a RAG execution."""

    query: str
    retrieval_recall: float
    context_relevance: float
    faithfulness: float
    citation_completeness: float
    overall_score: float
    citations_count: int
    retrieved_chunks_count: int
    details: dict[str, Any]


def evaluate_rag_execution(
    query: str,
    answer: str,
    retrieved_chunks: list[dict[str, Any]],
    expected_keywords: list[str] | None = None,
    expected_doc_ids: list[str] | None = None,
) -> RAGEvaluationReport:
    """Evaluate retrieval and generation quality deterministically on CPU."""
    query_tokens = set(re.findall(r"\w+", query.lower()))
    chunks_text = " ".join(c.get("text", "") for c in retrieved_chunks).lower()

    # 1. Retrieval Recall
    if expected_keywords:
        matched_kw = sum(1 for kw in expected_keywords if kw.lower() in chunks_text)
        retrieval_recall = matched_kw / len(expected_keywords)
    elif expected_doc_ids:
        retrieved_doc_ids = {c.get("document_id") for c in retrieved_chunks}
        matched_docs = sum(1 for did in expected_doc_ids if did in retrieved_doc_ids)
        retrieval_recall = matched_docs / len(expected_doc_ids)
    else:
        # Keyword overlap proxy
        matched = sum(1 for qt in query_tokens if qt in chunks_text)
        retrieval_recall = matched / max(1, len(query_tokens))

    # 2. Context Relevance
    if retrieved_chunks:
        relevant_chunks = 0
        for c in retrieved_chunks:
            c_text = c.get("text", "").lower()
            if any(qt in c_text for qt in query_tokens):
                relevant_chunks += 1
        context_relevance = relevant_chunks / len(retrieved_chunks)
    else:
        context_relevance = 0.0

    # 3. Faithfulness (Grounding in Context)
    answer_sentences = [s.strip() for s in re.split(r"[.?!]\s+", answer) if len(s.strip()) > 10]
    if answer_sentences:
        grounded_sentences = 0
        for s in answer_sentences:
            s_tokens = set(re.findall(r"\w+", s.lower()))
            overlap = s_tokens.intersection(set(re.findall(r"\w+", chunks_text)))
            if len(s_tokens) > 0 and (len(overlap) / len(s_tokens)) >= 0.35:
                grounded_sentences += 1
        faithfulness = grounded_sentences / len(answer_sentences)
    else:
        faithfulness = 1.0 if retrieved_chunks else 0.5

    # 4. Citation Completeness
    citation_markers = re.findall(r"\[Doc:\s*[^,]+,\s*Chunk:\s*\d+\]", answer)
    has_citations = len(citation_markers) > 0
    citation_completeness = 1.0 if (has_citations or not retrieved_chunks) else 0.0

    # Overall Score (Weighted combination)
    overall = round(
        0.3 * retrieval_recall
        + 0.3 * context_relevance
        + 0.3 * faithfulness
        + 0.1 * citation_completeness,
        4,
    )

    return RAGEvaluationReport(
        query=query,
        retrieval_recall=round(retrieval_recall, 4),
        context_relevance=round(context_relevance, 4),
        faithfulness=round(faithfulness, 4),
        citation_completeness=round(citation_completeness, 4),
        overall_score=overall,
        citations_count=len(citation_markers),
        retrieved_chunks_count=len(retrieved_chunks),
        details={
            "query_terms": list(query_tokens),
            "citations_found": citation_markers,
            "grounded_sentence_ratio": f"{int(faithfulness * 100)}%",
        },
    )
