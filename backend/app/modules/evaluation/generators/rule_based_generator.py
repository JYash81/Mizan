"""Rule-Based Local CPU Examination Question Generator.

Extracts grounded factual, procedural, conceptual, numerical, and unanswerable questions
directly from Gate 1 approved masked business text without calling external paid LLMs.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.models.evaluation import CaseCategory, DifficultyLevel, SplitType
from app.modules.evaluation.generators.base import (
    ExamGenerator,
    GeneratedCaseCandidate,
)


def compute_split(suite_id: str, question: str) -> SplitType:
    """Deterministically assign evaluation split using stable SHA-256 hashing."""
    h = hashlib.sha256(f"{suite_id}:{question}".encode()).hexdigest()
    val = int(h[:8], 16) % 100
    if val < 60:
        return SplitType.DEVELOPMENT  # 60%
    elif val < 80:
        return SplitType.VALIDATION   # 20%
    else:
        return SplitType.HOLDOUT      # 20%



class RuleBasedExamGenerator(ExamGenerator):
    """Deterministic, local CPU exam generator operating on masked document corpora."""

    def generate_candidates(
        self,
        masked_documents: list[dict[str, Any]],
        target_count: int = 10,
        language: str = "en",
        categories: list[CaseCategory] | None = None,
        difficulty_distribution: dict[DifficultyLevel, float] | None = None,
        include_unanswerable: bool = True,
        **kwargs: Any,
    ) -> list[GeneratedCaseCandidate]:
        candidates: list[GeneratedCaseCandidate] = []

        if not masked_documents:
            return candidates

        # 1. Parse propositions from each masked document
        propositions: list[dict[str, Any]] = []
        for doc in masked_documents:
            doc_id = doc.get("document_id", "doc-unknown")
            text = doc.get("text", "")
            if not text.strip():
                continue

            # Split by sentences with character offset tracking
            for match in re.finditer(r"([^.?!]+[.?!])", text):
                raw_sent = match.group(0).strip()
                if len(raw_sent) < 25:  # skip trivial sentences
                    continue

                propositions.append(
                    {
                        "document_id": doc_id,
                        "text": raw_sent,
                        "start_offset": match.start(),
                        "end_offset": match.end(),
                    }
                )

        if not propositions:
            return candidates

        # 2. Extract categorized questions from propositions
        for prop in propositions:
            if len(candidates) >= target_count:
                break

            sent_text = prop["text"]

            # Category A: NUMERICAL (checks for numbers, currency, percentages)
            if re.search(r"\b\d+(?:,\d+)*(?:\.\d+)?\b|\bAED\b|\bUSD\b|%|\bpercent\b", sent_text, re.IGNORECASE):
                # Identify topic
                topic_match = re.search(r"(?:for|regarding|exceeding|of|to)\s+([A-Za-z0-9_\s]{4,35})", sent_text, re.IGNORECASE)
                topic = topic_match.group(1).strip() if topic_match else "the specified operation"
                question = f"What numerical limit, threshold, or value is specified for {topic}?"
                candidates.append(
                    GeneratedCaseCandidate(
                        question=question,
                        expected_answer=sent_text,
                        category=CaseCategory.NUMERICAL,
                        difficulty=DifficultyLevel.HARD,
                        language=language,
                        is_unanswerable=False,
                        source_document_id=prop["document_id"],
                        source_offset_start=prop["start_offset"],
                        source_offset_end=prop["end_offset"],
                        evidence_text=sent_text,
                    )
                )
                continue

            # Category B: PROCEDURAL (checks for requirements, steps, approvals)
            if re.search(r"\b(?:must|shall|require|approval|procedure|step|prior to|mandatory)\b", sent_text, re.IGNORECASE):
                clause_match = re.search(r"\b(?:require[s]?|must|shall)\s+([A-Za-z0-9_\s\-]{5,50})", sent_text, re.IGNORECASE)
                clause = clause_match.group(1).strip() if clause_match else "regulatory compliance"
                question = f"What is required or mandated regarding {clause}?"
                candidates.append(
                    GeneratedCaseCandidate(
                        question=question,
                        expected_answer=sent_text,
                        category=CaseCategory.PROCEDURAL,
                        difficulty=DifficultyLevel.MEDIUM,
                        language=language,
                        is_unanswerable=False,
                        source_document_id=prop["document_id"],
                        source_offset_start=prop["start_offset"],
                        source_offset_end=prop["end_offset"],
                        evidence_text=sent_text,
                    )
                )
                continue

            # Category C: CONCEPTUAL (definitions or policy purposes)
            if re.search(r"\b(?:defined as|refers to|purpose of|stands for|governs)\b", sent_text, re.IGNORECASE):
                question = f"According to policy, what does the approved documentation specify regarding '{sent_text[:40]}...'?"
                candidates.append(
                    GeneratedCaseCandidate(
                        question=question,
                        expected_answer=sent_text,
                        category=CaseCategory.CONCEPTUAL,
                        difficulty=DifficultyLevel.MEDIUM,
                        language=language,
                        is_unanswerable=False,
                        source_document_id=prop["document_id"],
                        source_offset_start=prop["start_offset"],
                        source_offset_end=prop["end_offset"],
                        evidence_text=sent_text,
                    )
                )
                continue

            # Category D: FACTUAL
            if len(candidates) < target_count:
                question = f"What fact does the business documentation state regarding '{sent_text[:35]}'?"
                candidates.append(
                    GeneratedCaseCandidate(
                        question=question,
                        expected_answer=sent_text,
                        category=CaseCategory.FACTUAL,
                        difficulty=DifficultyLevel.EASY,
                        language=language,
                        is_unanswerable=False,
                        source_document_id=prop["document_id"],
                        source_offset_start=prop["start_offset"],
                        source_offset_end=prop["end_offset"],
                        evidence_text=sent_text,
                    )
                )

        # 3. Add UNANSWERABLE cases (adversarial / hallucination test cases)
        if include_unanswerable and len(candidates) < target_count:
            unanswerable_templates = [
                (
                    "What is the company's policy on personal cryptocurrency trading using corporate debit cards?",
                    "The provided documentation does not contain information or authorization regarding cryptocurrency trading.",
                ),
                (
                    "What are the specific guidelines for third-party drone usage on company premises?",
                    "The provided documentation does not contain guidelines regarding drone usage.",
                ),
                (
                    "What is the reimbursement procedure for international space travel expenditures?",
                    "The approved documentation does not mention or authorize space travel expenditures.",
                ),
            ]
            first_doc_id = masked_documents[0].get("document_id", "doc-1")
            for q_text, ans_text in unanswerable_templates:
                if len(candidates) >= target_count:
                    break
                candidates.append(
                    GeneratedCaseCandidate(
                        question=q_text,
                        expected_answer=ans_text,
                        category=CaseCategory.UNANSWERABLE,
                        difficulty=DifficultyLevel.HARD,
                        language=language,
                        is_unanswerable=True,
                        source_document_id=first_doc_id,
                        source_offset_start=0,
                        source_offset_end=0,
                        evidence_text="",
                        metadata={"is_adversarial_abstention_check": True},
                    )
                )

        return candidates[:target_count]
