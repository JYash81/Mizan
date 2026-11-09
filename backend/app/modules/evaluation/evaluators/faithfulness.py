"""Faithfulness Evaluator measuring whether generated claims are supported by context."""

from __future__ import annotations

import re
from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


def extract_claims(text: str) -> list[str]:
    """Decompose answer into atomic claims by punctuation boundaries."""
    # Split by periods, exclamation marks, question marks, or bullet lines
    raw_parts = re.split(r"[.?!]\s+|\n+", text)
    claims = []
    for part in raw_parts:
        cleaned = part.strip()
        # Filter trivial conversational wrappers
        if len(cleaned) > 15 and not cleaned.lower().startswith(("based on", "according to", "in conclusion")):
            claims.append(cleaned)
    return claims


class FaithfulnessEvaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "faithfulness"

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
                details={"message": "Faithfulness metric not applicable for unanswerable question."},
            )

        chunks = retrieved_chunks or []
        context_blob = " ".join(c.get("text", "") for c in chunks).lower()

        claims = extract_claims(actual_answer)

        if not claims:
            # If no substantive claims were made (e.g. valid abstention)
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=1.0,
                normalized_score=100.0,
                status=MetricStatus.MEASURED,
                evaluator_version=self.version,
                details={"message": "No substantive claims extracted; assumed compliant."},
            )

        supported_claims: list[str] = []
        unsupported_claims: list[str] = []

        for claim in claims:
            # Tokenize claim keywords (>3 chars)
            claim_words = [w for w in re.findall(r"\w+", claim.lower()) if len(w) > 3]
            if not claim_words:
                continue

            matches = sum(1 for w in claim_words if w in context_blob)
            match_ratio = matches / len(claim_words)

            if match_ratio >= 0.5:
                supported_claims.append(claim)
            else:
                unsupported_claims.append(claim)

        total_evaluated = len(supported_claims) + len(unsupported_claims)
        ratio = (len(supported_claims) / total_evaluated) if total_evaluated > 0 else 1.0

        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=round(ratio, 4),
            normalized_score=round(ratio * 100.0, 2),
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "total_claims": total_evaluated,
                "supported_claims_count": len(supported_claims),
                "unsupported_claims_count": len(unsupported_claims),
                "unsupported_claims": unsupported_claims[:5],
            },
        )
