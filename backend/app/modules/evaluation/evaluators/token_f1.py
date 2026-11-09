"""Token F1 (Precision, Recall, F1) evaluator with multilingual support."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.models.evaluation import MetricStatus
from app.modules.evaluation.evaluators.base import MetricEvaluator, MetricScoreResult


def tokenize(text: str) -> list[str]:
    """Tokenize text into alphanumeric words supporting English and Arabic characters."""
    return re.findall(r"[\w\u0600-\u06FF]+", text.lower())


class TokenF1Evaluator(MetricEvaluator):
    @property
    def metric_key(self) -> str:
        return "token_f1"

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
                details={"message": "Token F1 not applicable for unanswerable questions."},
            )

        pred_tokens = tokenize(actual_answer)
        gold_tokens = tokenize(expected_answer)

        if not pred_tokens or not gold_tokens:
            score = 100.0 if pred_tokens == gold_tokens else 0.0
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=1.0 if pred_tokens == gold_tokens else 0.0,
                normalized_score=score,
                status=MetricStatus.MEASURED,
                evaluator_version=self.version,
                details={"precision": 1.0, "recall": 1.0, "f1": 1.0},
            )

        common = Counter(pred_tokens) & Counter(gold_tokens)
        num_same = sum(common.values())

        if num_same == 0:
            return MetricScoreResult(
                metric_key=self.metric_key,
                raw_score=0.0,
                normalized_score=0.0,
                status=MetricStatus.MEASURED,
                evaluator_version=self.version,
                details={"precision": 0.0, "recall": 0.0, "f1": 0.0},
            )

        precision = 1.0 * num_same / len(pred_tokens)
        recall = 1.0 * num_same / len(gold_tokens)
        f1 = (2 * precision * recall) / (precision + recall)

        return MetricScoreResult(
            metric_key=self.metric_key,
            raw_score=round(f1, 4),
            normalized_score=round(f1 * 100.0, 2),
            status=MetricStatus.MEASURED,
            evaluator_version=self.version,
            details={
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "token_overlap_count": num_same,
            },
        )
