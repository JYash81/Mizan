"""Base interfaces and result containers for deterministic metric evaluators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.models.evaluation import MetricStatus


@dataclass
class MetricScoreResult:
    """Standardized quantitative evaluation outcome for a single metric."""

    metric_key: str
    raw_score: float
    normalized_score: float  # Guaranteed 0.0 - 100.0 scale
    status: MetricStatus
    evaluator_version: str = "1.0.0"
    score_scale: str = "0-100"
    details: dict[str, Any] = field(default_factory=dict)


class MetricEvaluator(ABC):
    """Abstract interface for all Mizan evaluation metric processors."""

    def __init__(self, version: str = "1.0.0"):
        self.version = version

    @property
    @abstractmethod
    def metric_key(self) -> str:
        """Unique key identifying the metric (e.g. 'exact_match', 'faithfulness')."""

    @abstractmethod
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
        """Compute score deterministically on CPU."""
